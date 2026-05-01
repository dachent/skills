Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$sharedOfficeModule = (Resolve-Path (Join-Path $PSScriptRoot '..\..\.shared\office-com\scripts\office_com_common.psm1')).Path

Import-Module $sharedOfficeModule -Force -DisableNameChecking

function Test-WindowsHost {
    if ($env:OS -ne 'Windows_NT') {
        throw 'This skill requires Windows with Microsoft Word installed.'
    }
}

function Resolve-FullPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [switch]$AllowMissing
    )

    if ($AllowMissing) {
        return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    }

    return (Resolve-Path -LiteralPath $Path).Path
}

function Ensure-ParentDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

function New-WordApplication {
    param(
        [bool]$Visible = $false
    )

    Test-WindowsHost
    Assert-OfficeComAvailable -AppName 'Word' | Out-Null

    try {
        $word = New-Object -ComObject Word.Application
    }
    catch {
        throw "Unable to start Word COM automation. Ensure Microsoft Word is installed and can be opened manually. $($_.Exception.Message)"
    }

    $word.Visible = $Visible
    $word.DisplayAlerts = 0
    return $word
}

function Open-WordDocument {
    param(
        [Parameter(Mandatory = $true)]
        $Word,

        [Parameter(Mandatory = $true)]
        [string]$InputPath,

        [bool]$ReadOnly = $false
    )

    $resolved = Resolve-FullPath -Path $InputPath
    return $Word.Documents.Open($resolved, $false, $ReadOnly)
}

function Save-WordDocument {
    param(
        [Parameter(Mandatory = $true)]
        $Document,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath,

        [int]$Format = 16
    )

    $resolved = Resolve-FullPath -Path $OutputPath -AllowMissing
    Ensure-ParentDirectory -Path $resolved
    $Document.SaveAs2($resolved, $Format)
    return $resolved
}

function Export-WordPdf {
    param(
        [Parameter(Mandatory = $true)]
        $Document,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    $resolved = Resolve-FullPath -Path $OutputPath -AllowMissing
    Ensure-ParentDirectory -Path $resolved
    $Document.ExportAsFixedFormat($resolved, 17)
    return $resolved
}

function Update-DocumentFields {
    param(
        [Parameter(Mandatory = $true)]
        $Document
    )

    foreach ($toc in @($Document.TablesOfContents)) {
        $toc.Update() | Out-Null
    }

    $Document.Fields.Update() | Out-Null
    $null = $Document.ComputeStatistics(2)
}

function Release-ComObject {
    param(
        [Parameter(ValueFromPipeline = $true)]
        $ComObject
    )

    process {
        if ($null -ne $ComObject) {
            try {
                [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($ComObject)
            }
            catch {
            }
        }
    }
}

function Close-WordAutomation {
    param(
        $Word,
        $Document,
        [switch]$SaveChanges
    )

    if ($null -ne $Document) {
        try {
            $Document.Close([bool]$SaveChanges)
        }
        catch {
        }
        Release-ComObject $Document
    }

    if ($null -ne $Word) {
        try {
            $Word.Quit()
        }
        catch {
        }
        Release-ComObject $Word
    }

    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
