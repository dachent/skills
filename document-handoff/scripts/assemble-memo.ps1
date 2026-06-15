param(
    [Parameter(Mandatory=$true)][string]$ProjectSlug,
    [Parameter(Mandatory=$true)][string]$OutputDir
)

$tmpDir  = Join-Path $OutputDir ".handoff\tmp"
$outFile = Join-Path $OutputDir "$ProjectSlug-memo.html"

$fragments = Get-ChildItem -Path $tmpDir -Filter "sec_*.html" -ErrorAction Stop |
             Sort-Object Name

if ($fragments.Count -eq 0) {
    Write-Error "No sec_*.html fragments found in: $tmpDir"
    exit 1
}

Write-Host "Assembling $($fragments.Count) fragments..."

$sb = [System.Text.StringBuilder]::new()
foreach ($f in $fragments) {
    [void]$sb.Append((Get-Content -Path $f.FullName -Raw -Encoding UTF8))
    [void]$sb.AppendLine()
}

[System.IO.File]::WriteAllText($outFile, $sb.ToString(), [System.Text.Encoding]::UTF8)

$kb = [math]::Round((Get-Item $outFile).Length / 1KB, 1)
Write-Host "Memo written: $outFile ($kb KB)"

Remove-Item -Path $tmpDir -Recurse -Force
Write-Host "Cleaned tmp dir: $tmpDir"
exit 0
