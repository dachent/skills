# install.ps1 — Deploy document-handoff skill to Claude Code skills directory
# Run from the control folder: .\install.ps1
# Or from anywhere: & "C:\full\path\to\install.ps1"

$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest   = "$env:USERPROFILE\.claude\skills\document-handoff"

Write-Host "Installing document-handoff skill..."
Write-Host "  Source: $source"
Write-Host "  Dest:   $dest"

New-Item -ItemType Directory -Path "$dest\scripts"   -Force | Out-Null
New-Item -ItemType Directory -Path "$dest\templates" -Force | Out-Null

Copy-Item "$source\SKILL.md"         "$dest\SKILL.md" -Force
Copy-Item "$source\scripts\*.js"     "$dest\scripts\" -Force
Copy-Item "$source\scripts\*.ps1"    "$dest\scripts\" -Force
Copy-Item "$source\templates\*"      "$dest\templates\" -Force

$files = Get-ChildItem $dest -Recurse -File
Write-Host "Installed $($files.Count) files:"
$files | ForEach-Object { Write-Host "  $($_.FullName.Replace($dest, '.'))" }
Write-Host "Done."
