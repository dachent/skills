param(
    [Parameter(Mandatory = $true)]
    [string]$WorkbookPath,

    [Parameter(Mandatory = $true)]
    [string]$QueryName,

    [Parameter(Mandatory = $true)]
    [string]$MFormulaPath,

    [Parameter(Mandatory = $true)]
    [string]$WorksheetName,

    [string]$StartCell = "A1"
)

# Test-fixture-only helper for xlsx-win's certification corpus (issue #78).
# Builds one genuine, self-contained Power Query M connection (a query plus
# a worksheet load) in a single Excel session, so corpus.py can keep
# generating a real -- not placeholder -- Power-Query-backed workbook to
# exercise the supervisor's refresh path end to end. This is NOT part of the
# shipped xlsx-win skill: authoring or editing Power Query M is a known,
# documented gap in the v2 job contract (see xlsx-win/README.md and
# xlsx-win/SKILL.md, "Known gaps").

$ErrorActionPreference = "Stop"
$excel = $null
$workbook = $null

try {
    $resolvedWorkbookPath = (Resolve-Path -LiteralPath $WorkbookPath -ErrorAction Stop).Path
    $formula = Get-Content -LiteralPath $MFormulaPath -Raw

    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.EnableEvents = $false
    $excel.AskToUpdateLinks = $false
    $excel.ScreenUpdating = $false
    $excel.AutomationSecurity = 3

    $workbook = $excel.Workbooks.Open($resolvedWorkbookPath, 0, $false)

    $query = $workbook.Queries.Add($QueryName, $formula)

    $worksheet = $workbook.Worksheets.Add()
    $worksheet.Name = $WorksheetName

    $connectionString = "OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=`$Workbook`$;Location=$QueryName;Extended Properties=`"`""
    $commandText = "SELECT * FROM [$QueryName]"

    $listObject = $worksheet.ListObjects.Add(3, $connectionString, $true, 0, $worksheet.Range($StartCell))
    $queryTable = $listObject.QueryTable
    $queryTable.CommandText = $commandText
    $queryTable.CommandType = 2
    $queryTable.BackgroundQuery = $false
    $queryTable.Refresh($false) | Out-Null

    $connection = $null
    try {
        $connection = $queryTable.WorkbookConnection
    }
    catch {
        $connection = $null
    }

    $workbook.Save()

    # Release every intermediate COM object explicitly (same discipline as
    # the fix for the real Power-Query RCW leak in StepRunner.cs): this
    # helper's own caller (run_corpus.py) asserts zero surviving EXCEL.EXE
    # processes immediately after this script exits.
    if ($null -ne $connection) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($connection)
    }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($queryTable)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($listObject)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($worksheet)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($query)

    exit 0
}
catch {
    Write-Error -Message $_.Exception.Message
    exit 1
}
finally {
    if ($null -ne $workbook) {
        $workbook.Close($false) | Out-Null
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook)
    }

    if ($null -ne $excel) {
        $excel.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
    }

    [gc]::Collect()
    [gc]::WaitForPendingFinalizers()
    [gc]::Collect()
}
