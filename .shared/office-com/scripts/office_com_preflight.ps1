[CmdletBinding()]
param(
    [ValidateSet('Excel', 'PowerPoint', 'Word')]
    [string[]]$Apps = @('Excel', 'PowerPoint', 'Word')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'office_com_common.psm1') -Force -DisableNameChecking

$result = Get-OfficeComPreflightResult -Apps $Apps
$result | ConvertTo-Json -Depth 8

if ($result.can_use_com) {
    exit 0
}

exit 2
