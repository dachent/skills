param(
    [Parameter(Mandatory = $true)]
    [string]$WorkbookPath,

    [Parameter(Mandatory = $true)]
    [ValidateSet("upsert-query", "load-worksheet", "load-model", "delete-query")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$QueryName,

    [string]$MFormula,

    [string]$MFormulaPath,

    [string]$WorksheetName,

    [string]$StartCell = "A1",

    [string]$LogPath,

    [string]$JsonPath,

    [switch]$EnableMacros,

    [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"
$global:ExitCode = 1
$script:excel = $null
$script:workbook = $null
$startTime = Get-Date
$resolvedWorkbookPath = $WorkbookPath
$logReady = $false
$macroPolicy = if ($EnableMacros.IsPresent) { "enabled" } else { "disabled" }
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$refreshScript = Join-Path $scriptDir "refresh_excel.ps1"
$actionPayload = [ordered]@{}
$resolvedMFormula = $null
$sharedOfficeModule = (Resolve-Path (Join-Path $PSScriptRoot '..\..\.shared\office-com\scripts\office_com_common.psm1')).Path

Import-Module $sharedOfficeModule -Force -DisableNameChecking

function Ensure-ParentDirectory {
    param(
        [string]$PathValue
    )

    $dir = Split-Path -Path $PathValue -Parent
    if ([string]::IsNullOrWhiteSpace($dir) -eq $false -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

function Get-AbsolutePath {
    param(
        [string]$PathValue
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }

    try {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    catch {
        return $PathValue
    }
}

function New-ArtifactPath {
    param(
        [string]$BasePath,
        [string]$Kind,
        [string]$Extension
    )

    $leafBase = [System.IO.Path]::GetFileNameWithoutExtension($BasePath)
    if ([string]::IsNullOrWhiteSpace($leafBase)) {
        $leafBase = "workbook"
    }

    $safeLeaf = [regex]::Replace($leafBase, "[^A-Za-z0-9._-]", "_")
    $stamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 8)
    $fileName = "{0}-{1}-{2}-{3}.{4}" -f $safeLeaf, $Kind, $stamp, $suffix, $Extension
    return Join-Path ([System.IO.Path]::GetTempPath()) $fileName
}

function Resolve-ArtifactPath {
    param(
        [string]$RequestedPath,
        [string]$BasePath,
        [string]$Kind,
        [string]$Extension
    )

    if ([string]::IsNullOrWhiteSpace($RequestedPath)) {
        return (New-ArtifactPath -BasePath $BasePath -Kind $Kind -Extension $Extension)
    }

    return (Get-AbsolutePath -PathValue $RequestedPath)
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$timestamp [$Level] $Message"
    Write-Host $line
    if ($logReady) {
        Add-Content -Path $LogPath -Value $line
    }
}

function Get-ErrorInfo {
    param(
        [System.Management.Automation.ErrorRecord]$Record
    )

    $rawMessage = $Record.Exception.Message
    $normalized = $rawMessage.ToLowerInvariant()
    $errorKind = "runtime_error"
    $friendlyMessage = $rawMessage

    if ($rawMessage.StartsWith("OFFICE_PRECHECK::")) {
        $parts = $rawMessage.Split("::", 3)
        $errorKind = if ($parts.Length -ge 2) { $parts[1] } else { "excel_com_unavailable" }
        $friendlyMessage = if ($parts.Length -ge 3) { $parts[2] } else { "Excel COM automation is unavailable in this session." }
    }
    elseif ($rawMessage.StartsWith("REFRESH_FAILED::")) {
        $parts = $rawMessage.Split("::", 3)
        $errorKind = if ($parts.Length -ge 2) { $parts[1] } else { "refresh_failed" }
        $friendlyMessage = if ($parts.Length -ge 3) { $parts[2] } else { "refresh_excel.ps1 failed." }
    }
    elseif ($rawMessage.StartsWith("INVALID_ARGUMENTS::")) {
        $errorKind = "invalid_arguments"
        $friendlyMessage = $rawMessage.Substring("INVALID_ARGUMENTS::".Length)
    }
    elseif ($rawMessage.StartsWith("MISSING_QUERY::")) {
        $errorKind = "missing_query"
        $friendlyMessage = $rawMessage.Substring("MISSING_QUERY::".Length)
    }
    elseif ($rawMessage.StartsWith("DESTINATION_CONFLICT::")) {
        $errorKind = "destination_conflict"
        $friendlyMessage = $rawMessage.Substring("DESTINATION_CONFLICT::".Length)
    }
    elseif ($rawMessage.StartsWith("UNSUPPORTED_FEATURE::")) {
        $errorKind = "unsupported_feature"
        $friendlyMessage = $rawMessage.Substring("UNSUPPORTED_FEATURE::".Length)
    }
    elseif (
        $normalized.Contains("cannot find path") -or
        $normalized.Contains("workbook path does not exist")
    ) {
        $errorKind = "missing_workbook"
        $friendlyMessage = "Workbook path does not exist: $WorkbookPath"
    }
    elseif (
        $normalized.Contains("class not registered") -or
        $normalized.Contains("activex component can't create object")
    ) {
        $errorKind = "excel_not_installed"
        $friendlyMessage = "Excel COM automation could not be created. Confirm that Microsoft 365 Excel desktop is installed and registered correctly."
    }
    elseif (
        $normalized.Contains("specified logon session does not exist") -or
        $normalized.Contains("retrieving the com class factory")
    ) {
        $errorKind = "excel_com_unavailable"
        $friendlyMessage = "Excel COM automation is unavailable in this session. Run Power Query operations from an interactive Windows desktop session."
    }

    [pscustomobject]@{
        kind = $errorKind
        message = $friendlyMessage
        raw_message = $rawMessage
    }
}

function Write-StatusJson {
    param(
        [string]$Status,
        [string]$Message,
        [string]$ResolvedWorkbookPath = $null,
        [int]$DurationSeconds = 0,
        [string]$ErrorKind = $null,
        [hashtable]$ExtraPayload = @{}
    )

    $payload = [ordered]@{
        status = $Status
        action = $Action
        message = $Message
        workbook = $ResolvedWorkbookPath
        query_name = $QueryName
        macro_policy = $macroPolicy
        log_path = (Get-AbsolutePath -PathValue $LogPath)
        json_path = (Get-AbsolutePath -PathValue $JsonPath)
        duration_seconds = $DurationSeconds
        timestamp = (Get-Date).ToString("s")
        exit_code = $global:ExitCode
    }

    if ([string]::IsNullOrWhiteSpace($ErrorKind) -eq $false) {
        $payload.error_kind = $ErrorKind
    }

    foreach ($entry in $ExtraPayload.GetEnumerator()) {
        $payload[$entry.Key] = $entry.Value
    }

    $payload | ConvertTo-Json -Depth 8 | Set-Content -Path $JsonPath -Encoding UTF8
}

function Open-ExcelSession {
    param(
        [string]$ResolvedPath
    )

    $preflight = Get-OfficeComPreflightResult -Apps @('Excel')
    $failureInfo = Get-OfficePreflightFailureInfo -Preflight $preflight -AppName 'Excel'
    if ($null -ne $failureInfo) {
        throw "OFFICE_PRECHECK::$($failureInfo.error_kind)::$($failureInfo.message)"
    }

    $script:excel = New-Object -ComObject Excel.Application
    $script:excel.Visible = $false
    $script:excel.DisplayAlerts = $false
    $script:excel.EnableEvents = $false
    $script:excel.AskToUpdateLinks = $false
    $script:excel.Interactive = $false
    $script:excel.ScreenUpdating = $false
    $script:excel.AutomationSecurity = if ($EnableMacros.IsPresent) { 1 } else { 3 }

    Write-Log "Excel COM instance created."

    $script:workbook = $script:excel.Workbooks.Open($ResolvedPath, 0, $false)
    Write-Log "Workbook opened."

    if ($script:workbook.ReadOnly) {
        throw "Workbook opened read-only: $ResolvedPath"
    }
}

function Close-ExcelSession {
    param(
        [bool]$SaveChanges = $false
    )

    if ($script:workbook -ne $null) {
        try {
            Write-Log "Closing workbook."
            $script:workbook.Close($SaveChanges) | Out-Null
        }
        catch {
            Write-Log "Failed to close workbook cleanly: $($_.Exception.Message)" "WARN"
        }
    }

    if ($script:excel -ne $null) {
        try {
            Write-Log "Quitting Excel."
            $script:excel.Quit()
        }
        catch {
            Write-Log "Failed to quit Excel cleanly: $($_.Exception.Message)" "WARN"
        }
    }

    if ($script:workbook -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($script:workbook)
        $script:workbook = $null
    }

    if ($script:excel -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($script:excel)
        $script:excel = $null
    }

    [gc]::Collect()
    [gc]::WaitForPendingFinalizers()
}

function Escape-SqlIdentifier {
    param(
        [string]$Value
    )

    return $Value.Replace("]", "]]")
}

function Get-QueryConnectionString {
    param(
        [string]$Name
    )

    return "OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=`$Workbook$;Location=$Name;Extended Properties=`"`""
}

function Get-QueryCommandText {
    param(
        [string]$Name
    )

    $escaped = Escape-SqlIdentifier -Value $Name
    return "SELECT * FROM [$escaped]"
}

function Get-OleDbConnectionString {
    param(
        $WorkbookConnection
    )

    try {
        return [string]$WorkbookConnection.OLEDBConnection.Connection
    }
    catch {
        return ""
    }
}

function Test-ConnectionMatchesQuery {
    param(
        [string]$ConnectionString,
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($ConnectionString)) {
        return $false
    }

    $normalized = $ConnectionString.Replace([string][char]0, "")
    $pattern = "Provider=Microsoft\.Mashup\.OleDb\.1;.*Location=" + [regex]::Escape($Name) + "(;|$)"
    return $normalized -match $pattern
}

function Try-GetWorkbookQuery {
    param(
        $Workbook,
        [string]$Name
    )

    for ($i = 1; $i -le $Workbook.Queries.Count; $i++) {
        $candidate = $Workbook.Queries.Item($i)
        if ($candidate.Name -ieq $Name) {
            return $candidate
        }
    }

    return $null
}

function Ensure-WorkbookQuery {
    param(
        $Workbook,
        [string]$Name,
        [string]$Formula
    )

    $result = [ordered]@{
        query_exists_before = $false
        query_created = $false
        query_updated = $false
    }

    $query = Try-GetWorkbookQuery -Workbook $Workbook -Name $Name
    if ($null -ne $query) {
        $result.query_exists_before = $true
        if ([string]::IsNullOrWhiteSpace($Formula) -eq $false) {
            if ($query.Formula -ne $Formula) {
                $query.Formula = $Formula
                $result.query_updated = $true
            }
        }

        return [pscustomobject]@{
            Query = $query
            Result = $result
        }
    }

    if ([string]::IsNullOrWhiteSpace($Formula)) {
        throw "MISSING_QUERY::Query '$Name' was not found and no M formula was provided."
    }

    $query = $Workbook.Queries.Add($Name, $Formula)
    $result.query_created = $true

    return [pscustomobject]@{
        Query = $query
        Result = $result
    }
}

function Get-OrCreateWorksheet {
    param(
        $Workbook,
        [string]$Name
    )

    for ($i = 1; $i -le $Workbook.Worksheets.Count; $i++) {
        $candidate = $Workbook.Worksheets.Item($i)
        if ($candidate.Name -ieq $Name) {
            return [pscustomobject]@{
                Worksheet = $candidate
                Created = $false
            }
        }
    }

    $worksheet = $Workbook.Worksheets.Add()
    $worksheet.Name = $Name
    return [pscustomobject]@{
        Worksheet = $worksheet
        Created = $true
    }
}

function Get-WorksheetLoads {
    param(
        $Workbook,
        [string]$Name
    )

    $loads = @()

    for ($wsIndex = 1; $wsIndex -le $Workbook.Worksheets.Count; $wsIndex++) {
        $worksheet = $Workbook.Worksheets.Item($wsIndex)

        for ($loIndex = 1; $loIndex -le $worksheet.ListObjects.Count; $loIndex++) {
            $listObject = $worksheet.ListObjects.Item($loIndex)
            $queryTable = $null
            $workbookConnection = $null

            try {
                $queryTable = $listObject.QueryTable
            }
            catch {
                continue
            }

            try {
                $workbookConnection = $queryTable.WorkbookConnection
            }
            catch {
                continue
            }

            $connectionString = Get-OleDbConnectionString -WorkbookConnection $workbookConnection
            if (-not (Test-ConnectionMatchesQuery -ConnectionString $connectionString -Name $Name)) {
                continue
            }

            $rowCount = 0
            try {
                if ($null -ne $listObject.DataBodyRange) {
                    $rowCount = [int]$listObject.DataBodyRange.Rows.Count
                }
            }
            catch {
                $rowCount = 0
            }

            $loads += [pscustomobject]@{
                LoadType = "listobject"
                Worksheet = $worksheet
                WorksheetName = $worksheet.Name
                StartCell = $listObject.Range.Cells.Item(1, 1).Address($false, $false)
                ListObject = $listObject
                QueryTable = $queryTable
                WorkbookConnection = $workbookConnection
                RowCount = $rowCount
            }
        }
    }

    return $loads
}

function Get-RelatedConnections {
    param(
        $Workbook,
        [string]$Name
    )

    $connections = @()

    for ($i = 1; $i -le $Workbook.Connections.Count; $i++) {
        $connection = $Workbook.Connections.Item($i)
        $connectionString = Get-OleDbConnectionString -WorkbookConnection $connection
        if (Test-ConnectionMatchesQuery -ConnectionString $connectionString -Name $Name) {
            $connections += $connection
        }
    }

    return $connections
}

function Get-ModelLoads {
    param(
        $Workbook,
        [string]$Name
    )

    $modelLoads = @()

    try {
        $count = $Workbook.Model.ModelTables.Count
    }
    catch {
        return $modelLoads
    }

    for ($i = 1; $i -le $count; $i++) {
        $modelTable = $Workbook.Model.ModelTables.Item($i)
        $sourceConnection = $null

        try {
            $sourceConnection = $modelTable.SourceWorkbookConnection
        }
        catch {
            continue
        }

        $connectionString = Get-OleDbConnectionString -WorkbookConnection $sourceConnection
        if (-not (Test-ConnectionMatchesQuery -ConnectionString $connectionString -Name $Name)) {
            continue
        }

        $recordCount = $null
        try {
            $recordCount = [int]$modelTable.RecordCount
        }
        catch {
            $recordCount = $null
        }

        $modelLoads += [pscustomobject]@{
            ModelTable = $modelTable
            TableName = $modelTable.Name
            RecordCount = $recordCount
            SourceWorkbookConnection = $sourceConnection
        }
    }

    return $modelLoads
}

function Remove-WorksheetLoad {
    param(
        $Load
    )

    if ($null -eq $Load) {
        return
    }

    $connectionName = $null
    try {
        $connectionName = $Load.WorkbookConnection.Name
    }
    catch {
        $connectionName = $null
    }

    if ($Load.LoadType -eq "listobject") {
        $Load.ListObject.Delete()
    }
    else {
        $Load.QueryTable.Delete()
    }

    if ([string]::IsNullOrWhiteSpace($connectionName) -eq $false) {
        try {
            $Load.WorkbookConnection.Delete()
        }
        catch {
            Write-Log "Workbook connection '$connectionName' could not be deleted after removing the worksheet load: $($_.Exception.Message)" "WARN"
        }
    }
}

function Assert-WorksheetDestinationAvailable {
    param(
        $Worksheet,
        [string]$CellAddress,
        [object[]]$ExistingLoads
    )

    $targetRange = $Worksheet.Range($CellAddress)

    foreach ($load in $ExistingLoads) {
        if ($load.WorksheetName -ieq $Worksheet.Name -and $load.StartCell -ieq $CellAddress) {
            return
        }
    }

    try {
        $existingTable = $targetRange.ListObject
        if ($null -ne $existingTable) {
            throw "DESTINATION_CONFLICT::Worksheet destination $($Worksheet.Name)!$CellAddress is already inside table '$($existingTable.Name)'."
        }
    }
    catch {
        if ($_.Exception.Message.StartsWith("DESTINATION_CONFLICT::")) {
            throw
        }
    }

    $value = $targetRange.Value2
    if ($null -ne $value -and [string]::IsNullOrWhiteSpace([string]$value) -eq $false) {
        throw "DESTINATION_CONFLICT::Worksheet destination $($Worksheet.Name)!$CellAddress already contains data."
    }
}

function Invoke-RefreshWorkflow {
    param(
        [string]$ResolvedPath
    )

    if (-not (Test-Path -LiteralPath $refreshScript)) {
        throw "UNSUPPORTED_FEATURE::refresh_excel.ps1 was not found next to power_query_excel.ps1."
    }

    $powershellExe = (Get-Command powershell -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if ([string]::IsNullOrWhiteSpace($powershellExe)) {
        throw "UNSUPPORTED_FEATURE::powershell.exe was not found for nested refresh execution."
    }

    $refreshLogPath = Resolve-ArtifactPath -RequestedPath $null -BasePath $ResolvedPath -Kind "refresh-helper" -Extension "log"
    $refreshJsonPath = Resolve-ArtifactPath -RequestedPath $null -BasePath $ResolvedPath -Kind "refresh-helper" -Extension "json"
    $args = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $refreshScript,
        "-WorkbookPath", $ResolvedPath,
        "-LogPath", $refreshLogPath,
        "-JsonPath", $refreshJsonPath,
        "-TimeoutSeconds", $TimeoutSeconds
    )

    if ($EnableMacros.IsPresent) {
        $args += "-EnableMacros"
    }

    Write-Log "Refreshing workbook through refresh_excel.ps1."
    & $powershellExe @args | Out-Null
    $refreshExitCode = $LASTEXITCODE

    $refreshPayload = $null
    if (Test-Path -LiteralPath $refreshJsonPath) {
        $refreshPayload = Get-Content -Path $refreshJsonPath -Raw | ConvertFrom-Json
    }

    if ($refreshExitCode -ne 0) {
        $refreshKind = if ($null -ne $refreshPayload -and $null -ne $refreshPayload.error_kind) { [string]$refreshPayload.error_kind } else { "refresh_failed" }
        $refreshMessage = if ($null -ne $refreshPayload -and $null -ne $refreshPayload.message) { [string]$refreshPayload.message } else { "refresh_excel.ps1 failed with exit code $refreshExitCode." }
        throw "REFRESH_FAILED::$refreshKind::$refreshMessage"
    }

    return [pscustomobject]@{
        json_path = $refreshJsonPath
        log_path = $refreshLogPath
        result = $refreshPayload
    }
}

try {
    $LogPath = Resolve-ArtifactPath -RequestedPath $LogPath -BasePath $WorkbookPath -Kind "power-query" -Extension "log"
    $JsonPath = Resolve-ArtifactPath -RequestedPath $JsonPath -BasePath $WorkbookPath -Kind "power-query" -Extension "json"

    Ensure-ParentDirectory -PathValue $LogPath
    Ensure-ParentDirectory -PathValue $JsonPath

    Set-Content -Path $LogPath -Value "" -Encoding UTF8
    $logReady = $true

    Write-Log "Starting Power Query action."
    Write-Log "Workbook argument: $WorkbookPath"
    Write-Log "Action: $Action"
    Write-Log "QueryName: $QueryName"
    Write-Log "Log file: $LogPath"
    Write-Log "JSON file: $JsonPath"
    Write-Log "TimeoutSeconds: $TimeoutSeconds"
    Write-Log "Macro policy: $macroPolicy"

    if (-not (Test-Path -LiteralPath $WorkbookPath)) {
        throw "Workbook path does not exist: $WorkbookPath"
    }

    $resolvedWorkbookPath = (Resolve-Path -LiteralPath $WorkbookPath -ErrorAction Stop).Path
    Write-Log "Resolved workbook path: $resolvedWorkbookPath"

    if (($Action -eq "upsert-query") -and [string]::IsNullOrWhiteSpace($MFormula)) {
        if ([string]::IsNullOrWhiteSpace($MFormulaPath)) {
            throw "INVALID_ARGUMENTS::upsert-query requires -MFormula or -MFormulaPath."
        }
    }

    if (($Action -eq "load-worksheet") -and [string]::IsNullOrWhiteSpace($WorksheetName)) {
        throw "INVALID_ARGUMENTS::load-worksheet requires -WorksheetName."
    }

    if ([string]::IsNullOrWhiteSpace($MFormula) -eq $false -and [string]::IsNullOrWhiteSpace($MFormulaPath) -eq $false) {
        throw "INVALID_ARGUMENTS::Specify either -MFormula or -MFormulaPath, not both."
    }

    if ([string]::IsNullOrWhiteSpace($MFormulaPath) -eq $false) {
        if (-not (Test-Path -LiteralPath $MFormulaPath)) {
            throw "INVALID_ARGUMENTS::M formula path does not exist: $MFormulaPath"
        }

        $resolvedMFormula = Get-Content -Path $MFormulaPath -Raw
    }
    else {
        $resolvedMFormula = $MFormula
    }

    Open-ExcelSession -ResolvedPath $resolvedWorkbookPath

    $queryResult = $null
    $requiresRefresh = $false

    switch ($Action) {
        "upsert-query" {
            $queryResult = Ensure-WorkbookQuery -Workbook $script:workbook -Name $QueryName -Formula $resolvedMFormula
            $actionPayload.query_exists_before = $queryResult.Result.query_exists_before
            $actionPayload.query_created = $queryResult.Result.query_created
            $actionPayload.query_updated = $queryResult.Result.query_updated
            $script:workbook.Save()
            $requiresRefresh = $true
        }
        "load-worksheet" {
            $queryResult = Ensure-WorkbookQuery -Workbook $script:workbook -Name $QueryName -Formula $resolvedMFormula
            $worksheetResult = Get-OrCreateWorksheet -Workbook $script:workbook -Name $WorksheetName
            $existingLoads = @(Get-WorksheetLoads -Workbook $script:workbook -Name $QueryName)
            Assert-WorksheetDestinationAvailable -Worksheet $worksheetResult.Worksheet -CellAddress $StartCell -ExistingLoads $existingLoads

            $matchingLoad = $existingLoads | Where-Object {
                $_.WorksheetName -ieq $worksheetResult.Worksheet.Name -and $_.StartCell -ieq $StartCell
            } | Select-Object -First 1

            $removedLoads = 0
            if ($null -eq $matchingLoad) {
                foreach ($load in $existingLoads) {
                    Remove-WorksheetLoad -Load $load
                    $removedLoads += 1
                }

                $connectionString = Get-QueryConnectionString -Name $QueryName
                $commandText = Get-QueryCommandText -Name $QueryName
                $listObject = $worksheetResult.Worksheet.ListObjects.Add(3, $connectionString, $true, 0, $worksheetResult.Worksheet.Range($StartCell))
                $listObject.QueryTable.CommandText = $commandText
                $listObject.QueryTable.CommandType = 2
                $listObject.QueryTable.BackgroundQuery = $false
                $listObject.QueryTable.Refresh($false) | Out-Null

                try {
                    $preferredConnectionName = "Query - $QueryName"
                    if ($listObject.QueryTable.WorkbookConnection.Name -ne $preferredConnectionName) {
                        $listObject.QueryTable.WorkbookConnection.Name = $preferredConnectionName
                    }
                }
                catch {
                    Write-Log "Worksheet load connection could not be renamed to the preferred name: $($_.Exception.Message)" "WARN"
                }

                $actionPayload.worksheet_load_created = $true
                $actionPayload.worksheet_load_reused = $false
            }
            else {
                $actionPayload.worksheet_load_created = $false
                $actionPayload.worksheet_load_reused = $true
            }

            $actionPayload.query_exists_before = $queryResult.Result.query_exists_before
            $actionPayload.query_created = $queryResult.Result.query_created
            $actionPayload.query_updated = $queryResult.Result.query_updated
            $actionPayload.created_sheet = $worksheetResult.Created
            $actionPayload.removed_worksheet_loads = $removedLoads
            $actionPayload.worksheet_name = $worksheetResult.Worksheet.Name
            $actionPayload.start_cell = $StartCell
            $script:workbook.Save()
            $requiresRefresh = $true
        }
        "load-model" {
            $queryResult = Ensure-WorkbookQuery -Workbook $script:workbook -Name $QueryName -Formula $resolvedMFormula
            try {
                $null = $script:workbook.Model.ModelTables.Count
            }
            catch {
                throw "UNSUPPORTED_FEATURE::Excel Data Model automation is unavailable in this environment."
            }

            $existingModelLoads = @(Get-ModelLoads -Workbook $script:workbook -Name $QueryName)
            $actionPayload.query_exists_before = $queryResult.Result.query_exists_before
            $actionPayload.query_created = $queryResult.Result.query_created
            $actionPayload.query_updated = $queryResult.Result.query_updated

            if ($existingModelLoads.Count -eq 0) {
                $relatedConnections = @(Get-RelatedConnections -Workbook $script:workbook -Name $QueryName)
                $legacyConnection = $relatedConnections | Where-Object { $_.Name -ieq "Query - $QueryName" } | Select-Object -First 1
                if ($null -eq $legacyConnection) {
                    $legacyConnection = $relatedConnections | Select-Object -First 1
                }

                if ($null -eq $legacyConnection) {
                    $legacyConnection = $script:workbook.Connections.Add("Query - $QueryName", "", (Get-QueryConnectionString -Name $QueryName), (Get-QueryCommandText -Name $QueryName), 2)
                }

                $null = $script:workbook.Model.AddConnection($legacyConnection)
                $actionPayload.model_load_created = $true
            }
            else {
                $actionPayload.model_load_created = $false
            }

            $script:workbook.Save()
            $requiresRefresh = $true
        }
        "delete-query" {
            $existingLoads = @(Get-WorksheetLoads -Workbook $script:workbook -Name $QueryName)
            $relatedConnections = @(Get-RelatedConnections -Workbook $script:workbook -Name $QueryName)
            $query = Try-GetWorkbookQuery -Workbook $script:workbook -Name $QueryName

            $deletedLoads = 0
            foreach ($load in $existingLoads) {
                Remove-WorksheetLoad -Load $load
                $deletedLoads += 1
            }

            $deletedConnections = 0
            $remainingConnections = @(Get-RelatedConnections -Workbook $script:workbook -Name $QueryName)
            for ($i = $remainingConnections.Count - 1; $i -ge 0; $i--) {
                $remainingConnections[$i].Delete()
                $deletedConnections += 1
            }

            $queryDeleted = $false
            if ($null -ne $query) {
                $query.Delete()
                $queryDeleted = $true
            }

            $actionPayload.deleted_worksheet_loads = $deletedLoads
            $actionPayload.deleted_connections = $deletedConnections
            $actionPayload.query_deleted = $queryDeleted
            $script:workbook.Save()
            $requiresRefresh = $false
        }
    }

    Close-ExcelSession -SaveChanges $false

    if ($requiresRefresh) {
        $refreshInfo = Invoke-RefreshWorkflow -ResolvedPath $resolvedWorkbookPath
        $actionPayload.refresh_log_path = $refreshInfo.log_path
        $actionPayload.refresh_json_path = $refreshInfo.json_path
        if ($null -ne $refreshInfo.result) {
            $actionPayload.refresh_status = $refreshInfo.result.status
        }
    }

    Open-ExcelSession -ResolvedPath $resolvedWorkbookPath

    switch ($Action) {
        "upsert-query" {
            $verifiedQuery = Try-GetWorkbookQuery -Workbook $script:workbook -Name $QueryName
            if ($null -eq $verifiedQuery) {
                throw "MISSING_QUERY::Query '$QueryName' was not found after upsert."
            }

            $actionPayload.verification = [ordered]@{
                query_exists = $true
            }
        }
        "load-worksheet" {
            $verifiedLoads = @(Get-WorksheetLoads -Workbook $script:workbook -Name $QueryName)
            $matchingLoad = $verifiedLoads | Where-Object {
                $_.WorksheetName -ieq $WorksheetName -and $_.StartCell -ieq $StartCell
            } | Select-Object -First 1

            if ($null -eq $matchingLoad) {
                throw "DESTINATION_CONFLICT::Worksheet load for query '$QueryName' was not found at $WorksheetName!$StartCell after refresh."
            }

            $connectionName = $null
            try {
                $connectionName = $matchingLoad.WorkbookConnection.Name
            }
            catch {
                $connectionName = $null
            }

            $actionPayload.verification = [ordered]@{
                worksheet_name = $WorksheetName
                start_cell = $StartCell
                row_count = $matchingLoad.RowCount
                connection_name = $connectionName
            }
        }
        "load-model" {
            $verifiedLoads = @(Get-ModelLoads -Workbook $script:workbook -Name $QueryName)
            if ($verifiedLoads.Count -eq 0) {
                throw "UNSUPPORTED_FEATURE::No related Data Model table was found after loading query '$QueryName' into the model."
            }

            $actionPayload.verification = [ordered]@{
                model_table_count = $verifiedLoads.Count
                model_tables = @(
                    $verifiedLoads | ForEach-Object {
                        [ordered]@{
                            table_name = $_.TableName
                            record_count = $_.RecordCount
                        }
                    }
                )
            }
        }
        "delete-query" {
            $verifiedQuery = Try-GetWorkbookQuery -Workbook $script:workbook -Name $QueryName
            $verifiedLoads = @(Get-WorksheetLoads -Workbook $script:workbook -Name $QueryName)
            $verifiedModelLoads = @(Get-ModelLoads -Workbook $script:workbook -Name $QueryName)
            $verifiedConnections = @(Get-RelatedConnections -Workbook $script:workbook -Name $QueryName)

            if ($null -ne $verifiedQuery -or $verifiedLoads.Count -gt 0 -or $verifiedModelLoads.Count -gt 0 -or $verifiedConnections.Count -gt 0) {
                throw "UNSUPPORTED_FEATURE::Query '$QueryName' still has workbook artifacts after delete."
            }

            $actionPayload.verification = [ordered]@{
                query_exists = $false
                related_connection_count = 0
                worksheet_load_count = 0
                model_table_count = 0
            }
        }
    }

    $duration = [int]((Get-Date) - $startTime).TotalSeconds
    $global:ExitCode = 0
    Write-StatusJson -Status "success" -Message "Power Query action completed successfully." -ResolvedWorkbookPath $resolvedWorkbookPath -DurationSeconds $duration -ExtraPayload $actionPayload
}
catch {
    $duration = [int]((Get-Date) - $startTime).TotalSeconds
    $errorInfo = Get-ErrorInfo -Record $_

    Write-Log "Power Query action failed after $duration second(s)." "ERROR"
    Write-Log "Error: $($errorInfo.message)" "ERROR"

    if ($errorInfo.raw_message -ne $errorInfo.message) {
        Write-Log "Original error: $($errorInfo.raw_message)" "WARN"
    }

    if ($_.ScriptStackTrace) {
        Write-Log "Stack: $($_.ScriptStackTrace)" "ERROR"
    }

    $global:ExitCode = 1
    Write-StatusJson -Status "error" -Message $errorInfo.message -ResolvedWorkbookPath $resolvedWorkbookPath -DurationSeconds $duration -ErrorKind $errorInfo.kind -ExtraPayload $actionPayload
}
finally {
    Close-ExcelSession -SaveChanges $false
    Write-Log "Exiting with code $global:ExitCode."
    exit $global:ExitCode
}
