param(
    [string]$JsonPath,

    [switch]$EnableMacros
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$refreshScript = Join-Path $scriptDir "refresh_excel.ps1"
$validatorScript = Join-Path $scriptDir "check_formula_errors.ps1"
$powerQueryScript = Join-Path $scriptDir "power_query_excel.ps1"
$powershellExe = (Get-Command powershell -ErrorAction SilentlyContinue | Select-Object -First 1).Source
$global:ExitCode = 1
$sharedOfficeModule = (Resolve-Path (Join-Path $PSScriptRoot '..\..\.shared\office-com\scripts\office_com_common.psm1')).Path

Import-Module $sharedOfficeModule -Force -DisableNameChecking

if ([string]::IsNullOrWhiteSpace($powershellExe)) {
    throw "powershell.exe was not found."
}

$macroPolicy = if ($EnableMacros.IsPresent) { "enabled" } else { "disabled" }
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("xlsx_win_self_test_" + [guid]::NewGuid().ToString("N"))
$spacedRoot = Join-Path $tempRoot "spaced path"
$passed = New-Object System.Collections.Generic.List[object]
$failed = New-Object System.Collections.Generic.List[object]
$skipped = New-Object System.Collections.Generic.List[object]

function Ensure-ParentDirectory {
    param(
        [string]$PathValue
    )

    $dir = Split-Path -Path $PathValue -Parent
    if ([string]::IsNullOrWhiteSpace($dir) -eq $false -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

function Resolve-JsonPath {
    param(
        [string]$RequestedPath
    )

    if ([string]::IsNullOrWhiteSpace($RequestedPath)) {
        return (Join-Path $tempRoot "self_test_results.json")
    }

    return [System.IO.Path]::GetFullPath($RequestedPath)
}

function Add-Outcome {
    param(
        [System.Collections.Generic.List[object]]$Bucket,
        [string]$Name,
        [string]$Message,
        [hashtable]$Details = @{}
    )

    $payload = [ordered]@{
        name = $Name
        message = $Message
    }

    foreach ($entry in $Details.GetEnumerator()) {
        $payload[$entry.Key] = $entry.Value
    }

    $Bucket.Add([pscustomobject]$payload)
}

function Invoke-PowerShellFile {
    param(
        [string]$ScriptPath,
        [string[]]$Arguments = @()
    )

    $output = & $powershellExe @("-ExecutionPolicy", "Bypass", "-File", $ScriptPath) @Arguments 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = ($output -join "`n")
    }
}

function Read-JsonFile {
    param(
        [string]$PathValue
    )

    if (-not (Test-Path -LiteralPath $PathValue)) {
        return $null
    }

    return (Get-Content -Path $PathValue -Raw | ConvertFrom-Json)
}

function New-ExcelWorkbook {
    param(
        [string]$PathValue,
        [scriptblock]$Configure
    )

    $excel = $null
    $workbook = $null

    try {
        Ensure-ParentDirectory -PathValue $PathValue
        Assert-OfficeComAvailable -AppName 'Excel' | Out-Null
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $false
        $excel.DisplayAlerts = $false
        $excel.EnableEvents = $false
        $excel.ScreenUpdating = $false
        $excel.AutomationSecurity = if ($EnableMacros.IsPresent) { 1 } else { 3 }
        $workbook = $excel.Workbooks.Add()
        & $Configure $workbook
        $excel.CalculateFullRebuild()
        while ($excel.CalculationState -ne 0) {
            Start-Sleep -Milliseconds 200
        }
        $workbook.SaveAs($PathValue, 51)
    }
    finally {
        if ($workbook -ne $null) {
            $workbook.Close($false) | Out-Null
            [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook)
        }

        if ($excel -ne $null) {
            $excel.Quit()
            [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
        }

        [gc]::Collect()
        [gc]::WaitForPendingFinalizers()
    }
}

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $spacedRoot -Force | Out-Null

    $okWorkbook = Join-Path $tempRoot "ok.xlsx"
    $errWorkbook = Join-Path $tempRoot "err.xlsx"
    $manyErrorsWorkbook = Join-Path $tempRoot "many_errors.xlsx"
    $notePath = Join-Path $tempRoot "note.txt"
    $spacedWorkbook = Join-Path $spacedRoot "space test.xlsx"
    $pqWorksheetWorkbook = Join-Path $tempRoot "pq_worksheet.xlsx"
    $pqModelWorkbook = Join-Path $tempRoot "pq_model.xlsx"
    $pqWorksheetFormulaPath = Join-Path $tempRoot "pq_worksheet.m"
    $pqModelFormulaPath = Join-Path $tempRoot "pq_model.m"

    New-ExcelWorkbook -PathValue $okWorkbook -Configure {
        param($Workbook)
        $sheet = $Workbook.Worksheets.Item(1)
        $sheet.Range("A1").Formula = "=1+1"
    }

    New-ExcelWorkbook -PathValue $errWorkbook -Configure {
        param($Workbook)
        $sheet = $Workbook.Worksheets.Item(1)
        $sheet.Range("A1").Formula = "=1/0"
        $sheet.Range("B1").Formula = "=1+1"
    }

    New-ExcelWorkbook -PathValue $manyErrorsWorkbook -Configure {
        param($Workbook)
        $sheet = $Workbook.Worksheets.Item(1)
        for ($row = 1; $row -le 60; $row++) {
            $sheet.Cells.Item($row, 1).Formula = "=NA()"
        }
    }

    New-ExcelWorkbook -PathValue $spacedWorkbook -Configure {
        param($Workbook)
        $sheet = $Workbook.Worksheets.Item(1)
        $sheet.Range("A1").Formula = "=2+2"
    }

    New-ExcelWorkbook -PathValue $pqWorksheetWorkbook -Configure {
        param($Workbook)
    }

    New-ExcelWorkbook -PathValue $pqModelWorkbook -Configure {
        param($Workbook)
    }

    Set-Content -Path $notePath -Value "not an xlsx" -Encoding UTF8
    Set-Content -Path $pqWorksheetFormulaPath -Value 'let Source = #table(type table [A = number], {{1},{2},{3}}) in Source' -Encoding UTF8
    Set-Content -Path $pqModelFormulaPath -Value 'let Source = #table(type table [A = number], {{10},{20}}) in Source' -Encoding UTF8

    $validatorOk = Invoke-PowerShellFile -ScriptPath $validatorScript -Arguments @("-WorkbookPath", $okWorkbook)
    $validatorOkJson = ($validatorOk.Output | ConvertFrom-Json)
    Assert-True ($validatorOk.ExitCode -eq 0 -and $validatorOkJson.status -eq "success") "Validator success path did not return status=success and exit=0."
    Add-Outcome -Bucket $passed -Name "validator-success" -Message "Validator success path passed." -Details @{ exit_code = $validatorOk.ExitCode }

    $validatorErr = Invoke-PowerShellFile -ScriptPath $validatorScript -Arguments @("-WorkbookPath", $errWorkbook)
    $validatorErrJson = ($validatorErr.Output | ConvertFrom-Json)
    Assert-True ($validatorErr.ExitCode -eq 2 -and $validatorErrJson.status -eq "errors_found" -and $validatorErrJson.total_errors -ge 1) "Validator error path did not report Excel error cells."
    Add-Outcome -Bucket $passed -Name "validator-findings" -Message "Validator findings path passed." -Details @{ total_errors = $validatorErrJson.total_errors }

    $validatorUnsupported = Invoke-PowerShellFile -ScriptPath $validatorScript -Arguments @("-WorkbookPath", $notePath)
    $validatorUnsupportedJson = ($validatorUnsupported.Output | ConvertFrom-Json)
    Assert-True ($validatorUnsupported.ExitCode -eq 1 -and $validatorUnsupportedJson.error_kind -eq "unsupported_extension") "Validator unsupported-extension path did not return unsupported_extension."
    Add-Outcome -Bucket $passed -Name "validator-unsupported" -Message "Validator unsupported-extension path passed."

    $missingWorkbook = Join-Path $tempRoot "missing.xlsx"
    $validatorMissing = Invoke-PowerShellFile -ScriptPath $validatorScript -Arguments @("-WorkbookPath", $missingWorkbook)
    $validatorMissingJson = ($validatorMissing.Output | ConvertFrom-Json)
    Assert-True ($validatorMissing.ExitCode -eq 1 -and $validatorMissingJson.error_kind -eq "missing_file") "Validator missing-file path did not return missing_file."
    Add-Outcome -Bucket $passed -Name "validator-missing" -Message "Validator missing-file path passed."

    $validatorMany = Invoke-PowerShellFile -ScriptPath $validatorScript -Arguments @("-WorkbookPath", $manyErrorsWorkbook)
    $validatorManyJson = ($validatorMany.Output | ConvertFrom-Json)
    $countValue = [int]$validatorManyJson.error_summary.'#N/A'.count
    Assert-True ($validatorMany.ExitCode -eq 2 -and $validatorManyJson.total_errors -eq 60 -and $countValue -eq 60) "Validator capped per-error counts incorrectly."
    Add-Outcome -Bucket $passed -Name "validator-counts" -Message "Validator large-count path passed." -Details @{ total_errors = $validatorManyJson.total_errors; count = $countValue }

    $refreshOkJsonPath = Join-Path $tempRoot "refresh_ok.json"
    $refreshOkLogPath = Join-Path $tempRoot "refresh_ok.log"
    $refreshOk = Invoke-PowerShellFile -ScriptPath $refreshScript -Arguments @("-WorkbookPath", $okWorkbook, "-JsonPath", $refreshOkJsonPath, "-LogPath", $refreshOkLogPath)
    $refreshOkJson = Read-JsonFile -PathValue $refreshOkJsonPath
    Assert-True ($refreshOk.ExitCode -eq 0 -and $refreshOkJson.status -eq "success" -and $refreshOkJson.macro_policy -eq $macroPolicy) "Refresh success path did not complete successfully."
    Add-Outcome -Bucket $passed -Name "refresh-success" -Message "Refresh success path passed." -Details @{ macro_policy = $refreshOkJson.macro_policy }

    $refreshMissingJsonPath = Join-Path $tempRoot "refresh_missing.json"
    $refreshMissingLogPath = Join-Path $tempRoot "refresh_missing.log"
    $refreshMissing = Invoke-PowerShellFile -ScriptPath $refreshScript -Arguments @("-WorkbookPath", $missingWorkbook, "-JsonPath", $refreshMissingJsonPath, "-LogPath", $refreshMissingLogPath)
    $refreshMissingJson = Read-JsonFile -PathValue $refreshMissingJsonPath
    Assert-True ($refreshMissing.ExitCode -eq 2 -and $refreshMissingJson.error_kind -eq "missing_workbook") "Refresh missing-workbook path did not return missing_workbook."
    Add-Outcome -Bucket $passed -Name "refresh-missing" -Message "Refresh missing-workbook path passed."

    $refreshSpacedJsonPath = Join-Path $tempRoot "refresh_spaced.json"
    $refreshSpacedLogPath = Join-Path $tempRoot "refresh_spaced.log"
    $refreshSpaced = Invoke-PowerShellFile -ScriptPath $refreshScript -Arguments @("-WorkbookPath", $spacedWorkbook, "-JsonPath", $refreshSpacedJsonPath, "-LogPath", $refreshSpacedLogPath)
    $refreshSpacedJson = Read-JsonFile -PathValue $refreshSpacedJsonPath
    Assert-True ($refreshSpaced.ExitCode -eq 0 -and $refreshSpacedJson.status -eq "success") "Refresh spaced-path path did not complete successfully."
    Add-Outcome -Bucket $passed -Name "refresh-spaced-path" -Message "Refresh spaced-path path passed."

    $refreshDefaultOne = Invoke-PowerShellFile -ScriptPath $refreshScript -Arguments @("-WorkbookPath", $okWorkbook)
    $refreshDefaultTwo = Invoke-PowerShellFile -ScriptPath $refreshScript -Arguments @("-WorkbookPath", $okWorkbook)
    $jsonPathOne = ([regex]::Match($refreshDefaultOne.Output, "JSON file: (?<path>.+)")).Groups["path"].Value.Trim()
    $jsonPathTwo = ([regex]::Match($refreshDefaultTwo.Output, "JSON file: (?<path>.+)")).Groups["path"].Value.Trim()
    Assert-True ([string]::IsNullOrWhiteSpace($jsonPathOne) -eq $false -and [string]::IsNullOrWhiteSpace($jsonPathTwo) -eq $false -and $jsonPathOne -ne $jsonPathTwo) "Refresh default artifact paths were not unique across runs."
    Assert-True ((Test-Path -LiteralPath $jsonPathOne) -and (Test-Path -LiteralPath $jsonPathTwo)) "Refresh default JSON artifacts were not created."
    Add-Outcome -Bucket $passed -Name "refresh-unique-artifacts" -Message "Refresh default artifact paths are unique across runs."

    $refreshMacroJsonPath = Join-Path $tempRoot "refresh_macros.json"
    $refreshMacroLogPath = Join-Path $tempRoot "refresh_macros.log"
    $refreshMacroArgs = @("-WorkbookPath", $okWorkbook, "-JsonPath", $refreshMacroJsonPath, "-LogPath", $refreshMacroLogPath)
    if ($EnableMacros.IsPresent) {
        $refreshMacroArgs += "-EnableMacros"
    }
    $refreshMacro = Invoke-PowerShellFile -ScriptPath $refreshScript -Arguments $refreshMacroArgs
    $refreshMacroJson = Read-JsonFile -PathValue $refreshMacroJsonPath
    Assert-True ($refreshMacro.ExitCode -eq 0 -and $refreshMacroJson.macro_policy -eq $macroPolicy) "Refresh macro policy was not reflected in JSON output."
    Add-Outcome -Bucket $passed -Name "refresh-macro-policy" -Message "Refresh macro policy is explicit in JSON."

    $pqUpsertJsonPath = Join-Path $tempRoot "pq_upsert.json"
    $pqUpsertLogPath = Join-Path $tempRoot "pq_upsert.log"
    $pqUpsertArgs = @(
        "-WorkbookPath", $pqWorksheetWorkbook,
        "-Action", "upsert-query",
        "-QueryName", "CodexPQ",
        "-MFormulaPath", $pqWorksheetFormulaPath,
        "-JsonPath", $pqUpsertJsonPath,
        "-LogPath", $pqUpsertLogPath
    )
    if ($EnableMacros.IsPresent) {
        $pqUpsertArgs += "-EnableMacros"
    }
    $pqUpsert = Invoke-PowerShellFile -ScriptPath $powerQueryScript -Arguments $pqUpsertArgs
    $pqUpsertJson = Read-JsonFile -PathValue $pqUpsertJsonPath
    Assert-True ($pqUpsert.ExitCode -eq 0 -and $pqUpsertJson.status -eq "success" -and $pqUpsertJson.query_created) "Power Query upsert-query action failed."
    Add-Outcome -Bucket $passed -Name "power-query-upsert" -Message "Power Query upsert-query action passed."

    $pqWorksheetJsonPath = Join-Path $tempRoot "pq_load_worksheet.json"
    $pqWorksheetLogPath = Join-Path $tempRoot "pq_load_worksheet.log"
    $pqWorksheetArgs = @(
        "-WorkbookPath", $pqWorksheetWorkbook,
        "-Action", "load-worksheet",
        "-QueryName", "CodexPQ",
        "-WorksheetName", "LoadedData",
        "-StartCell", "B3",
        "-JsonPath", $pqWorksheetJsonPath,
        "-LogPath", $pqWorksheetLogPath
    )
    if ($EnableMacros.IsPresent) {
        $pqWorksheetArgs += "-EnableMacros"
    }
    $pqWorksheet = Invoke-PowerShellFile -ScriptPath $powerQueryScript -Arguments $pqWorksheetArgs
    $pqWorksheetJson = Read-JsonFile -PathValue $pqWorksheetJsonPath
    Assert-True ($pqWorksheet.ExitCode -eq 0 -and $pqWorksheetJson.status -eq "success" -and $pqWorksheetJson.verification.row_count -eq 3) "Power Query worksheet load failed."
    Add-Outcome -Bucket $passed -Name "power-query-load-worksheet" -Message "Power Query worksheet load action passed." -Details @{ row_count = $pqWorksheetJson.verification.row_count }

    $pqDeleteJsonPath = Join-Path $tempRoot "pq_delete.json"
    $pqDeleteLogPath = Join-Path $tempRoot "pq_delete.log"
    $pqDeleteArgs = @(
        "-WorkbookPath", $pqWorksheetWorkbook,
        "-Action", "delete-query",
        "-QueryName", "CodexPQ",
        "-JsonPath", $pqDeleteJsonPath,
        "-LogPath", $pqDeleteLogPath
    )
    if ($EnableMacros.IsPresent) {
        $pqDeleteArgs += "-EnableMacros"
    }
    $pqDelete = Invoke-PowerShellFile -ScriptPath $powerQueryScript -Arguments $pqDeleteArgs
    $pqDeleteJson = Read-JsonFile -PathValue $pqDeleteJsonPath
    Assert-True ($pqDelete.ExitCode -eq 0 -and $pqDeleteJson.status -eq "success" -and -not $pqDeleteJson.verification.query_exists) "Power Query delete action failed."
    Add-Outcome -Bucket $passed -Name "power-query-delete" -Message "Power Query delete action passed."

    $pqModelJsonPath = Join-Path $tempRoot "pq_model.json"
    $pqModelLogPath = Join-Path $tempRoot "pq_model.log"
    $pqModelArgs = @(
        "-WorkbookPath", $pqModelWorkbook,
        "-Action", "load-model",
        "-QueryName", "CodexModel",
        "-MFormulaPath", $pqModelFormulaPath,
        "-JsonPath", $pqModelJsonPath,
        "-LogPath", $pqModelLogPath
    )
    if ($EnableMacros.IsPresent) {
        $pqModelArgs += "-EnableMacros"
    }
    $pqModel = Invoke-PowerShellFile -ScriptPath $powerQueryScript -Arguments $pqModelArgs
    $pqModelJson = Read-JsonFile -PathValue $pqModelJsonPath

    if ($pqModel.ExitCode -eq 0 -and $pqModelJson.status -eq "success") {
        Assert-True ($pqModelJson.verification.model_table_count -ge 1) "Power Query model load did not produce a model table."
        Add-Outcome -Bucket $passed -Name "power-query-load-model" -Message "Power Query model load action passed." -Details @{ model_table_count = $pqModelJson.verification.model_table_count }
    }
    elseif ($pqModelJson.error_kind -eq "unsupported_feature") {
        Add-Outcome -Bucket $skipped -Name "power-query-load-model" -Message "Data Model automation is unavailable in this environment." -Details @{ error_kind = $pqModelJson.error_kind }
    }
    else {
        throw "Power Query model load failed unexpectedly."
    }

    $summary = [ordered]@{
        status = if ($failed.Count -eq 0) { "success" } else { "error" }
        message = if ($failed.Count -eq 0) { "xlsx-win self-test passed." } else { "xlsx-win self-test found failures." }
        macro_policy = $macroPolicy
        temp_root = $tempRoot
        passed = $passed
        failed = $failed
        skipped = $skipped
        timestamp = (Get-Date).ToString("s")
        exit_code = if ($failed.Count -eq 0) { 0 } else { 1 }
    }

    $JsonPath = Resolve-JsonPath -RequestedPath $JsonPath
    Ensure-ParentDirectory -PathValue $JsonPath
    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $JsonPath -Encoding UTF8
    Write-Output ($summary | ConvertTo-Json -Depth 8)
    $global:ExitCode = if ($failed.Count -eq 0) { 0 } else { 1 }
}
catch {
    Add-Outcome -Bucket $failed -Name "self-test" -Message $_.Exception.Message
    $summary = [ordered]@{
        status = "error"
        message = "xlsx-win self-test failed."
        macro_policy = $macroPolicy
        temp_root = $tempRoot
        passed = $passed
        failed = $failed
        skipped = $skipped
        timestamp = (Get-Date).ToString("s")
        exit_code = 1
    }

    $JsonPath = Resolve-JsonPath -RequestedPath $JsonPath
    Ensure-ParentDirectory -PathValue $JsonPath
    $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $JsonPath -Encoding UTF8
    Write-Output ($summary | ConvertTo-Json -Depth 8)
    $global:ExitCode = 1
}
finally {
    exit $global:ExitCode
}
