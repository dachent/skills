#requires -Version 7.0

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RepositoryRoot {
    $toolsRoot = Split-Path -Parent $PSScriptRoot
    return [System.IO.Path]::GetFullPath($toolsRoot)
}

function Add-Failure {
    param(
        [Parameter(Mandatory)] $Failures,
        [Parameter(Mandatory)] [string]$Message
    )

    $Failures.Add($Message)
}

function ConvertFrom-SimpleYaml {
    param(
        [Parameter(Mandatory)] [string]$Content
    )

    $root = [ordered]@{}
    $stack = New-Object System.Collections.Generic.List[object]
    $stack.Add([pscustomobject]@{
        indent = -1
        map = $root
    })

    $lines = $Content -split "\r?\n"
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $trimmed = $line.Trim()
        if ($trimmed -eq '---' -or $trimmed.StartsWith('#')) {
            continue
        }

        $match = [regex]::Match($line, '^(?<indent>\s*)(?<key>[A-Za-z0-9_-]+):(?:\s*(?<value>.*))?$')
        if (-not $match.Success) {
            throw "Unsupported YAML syntax: $line"
        }

        $indent = $match.Groups['indent'].Value.Length
        $key = $match.Groups['key'].Value
        $rawValue = $match.Groups['value'].Value

        while ($stack.Count -gt 0 -and $stack[$stack.Count - 1].indent -ge $indent) {
            $stack.RemoveAt($stack.Count - 1)
        }

        $parent = $stack[$stack.Count - 1].map
        if ([string]::IsNullOrWhiteSpace($rawValue)) {
            $child = [ordered]@{}
            $parent[$key] = $child
            $stack.Add([pscustomobject]@{
                indent = $indent
                map = $child
            })
            continue
        }

        $value = $rawValue.Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $parent[$key] = $value
    }

    return $root
}

function Assert-RequiredString {
    param(
        [Parameter(Mandatory)] $InputObject,
        [Parameter(Mandatory)] [string]$PropertyName,
        [Parameter(Mandatory)] [string]$Context,
        [Parameter(Mandatory)] $Failures
    )

    $property = $InputObject.PSObject.Properties[$PropertyName]
    if ($null -eq $property) {
        Add-Failure -Failures $Failures -Message ("{0}: missing required property '{1}'." -f $Context, $PropertyName)
        return
    }

    $value = [string]$property.Value
    if ([string]::IsNullOrWhiteSpace($value)) {
        Add-Failure -Failures $Failures -Message ("{0}: property '{1}' must be a non-empty string." -f $Context, $PropertyName)
    }
}

function Get-SkillReferenceMatches {
    param(
        [Parameter(Mandatory)] [string]$Content
    )

    return [regex]::Matches($Content, '(?:scripts|references)/[A-Za-z0-9._/\-]+/?')
}

$repositoryRoot = Get-RepositoryRoot
$failures = New-Object System.Collections.Generic.List[string]

$agentFiles = Get-ChildItem -Path $repositoryRoot -Recurse -File -Filter 'openai.yaml' |
    Where-Object { $_.Directory.Name -eq 'agents' } |
    Sort-Object FullName

foreach ($agentFile in $agentFiles) {
    $context = $agentFile.FullName.Substring($repositoryRoot.Length + 1)
    $yamlObject = ConvertFrom-SimpleYaml -Content (Get-Content -LiteralPath $agentFile.FullName -Raw)

    if ($null -eq $yamlObject) {
        Add-Failure -Failures $failures -Message ("{0}: YAML file is empty or invalid." -f $context)
        continue
    }

    if (-not $yamlObject.Contains('interface') -or $null -eq $yamlObject['interface']) {
        Add-Failure -Failures $failures -Message ("{0}: missing required top-level 'interface' object." -f $context)
        continue
    }

    $interface = [pscustomobject]$yamlObject['interface']
    Assert-RequiredString -InputObject $interface -PropertyName 'display_name' -Context $context -Failures $failures
    Assert-RequiredString -InputObject $interface -PropertyName 'short_description' -Context $context -Failures $failures
    Assert-RequiredString -InputObject $interface -PropertyName 'default_prompt' -Context $context -Failures $failures
}

$skillFiles = Get-ChildItem -Path $repositoryRoot -Recurse -File -Filter 'SKILL.md' | Sort-Object FullName
foreach ($skillFile in $skillFiles) {
    $skillRoot = Split-Path -Parent $skillFile.FullName
    $skillName = Split-Path -Leaf $skillRoot
    $context = $skillFile.FullName.Substring($repositoryRoot.Length + 1)
    $content = Get-Content -LiteralPath $skillFile.FullName -Raw

    $frontMatterMatch = [regex]::Match($content, '^---\r?\n(?<yaml>[\s\S]*?)\r?\n---')
    if (-not $frontMatterMatch.Success) {
        Add-Failure -Failures $failures -Message ("{0}: missing YAML front matter." -f $context)
        continue
    }

    $frontMatter = ConvertFrom-SimpleYaml -Content $frontMatterMatch.Groups['yaml'].Value
    if ($null -eq $frontMatter) {
        Add-Failure -Failures $failures -Message ("{0}: YAML front matter is invalid." -f $context)
        continue
    }

    $frontMatterObject = [pscustomobject]$frontMatter
    Assert-RequiredString -InputObject $frontMatterObject -PropertyName 'name' -Context $context -Failures $failures
    Assert-RequiredString -InputObject $frontMatterObject -PropertyName 'description' -Context $context -Failures $failures

    $nameProperty = $frontMatterObject.PSObject.Properties['name']
    $frontMatterName = if ($null -ne $nameProperty) { [string]$nameProperty.Value } else { '' }
    if (-not [string]::IsNullOrWhiteSpace($frontMatterName) -and $frontMatterName -ne $skillName) {
        Add-Failure -Failures $failures -Message ("{0}: front matter name '{1}' does not match directory name '{2}'." -f $context, $frontMatterName, $skillName)
    }

    $referenceMatches = Get-SkillReferenceMatches -Content $content
    foreach ($referenceMatch in $referenceMatches) {
        $relativeReference = $referenceMatch.Value
        $resolvedReference = Join-Path $skillRoot ($relativeReference -replace '/', '\')
        if (-not (Test-Path -LiteralPath $resolvedReference)) {
            Add-Failure -Failures $failures -Message ("{0}: referenced path does not exist: {1}" -f $context, $relativeReference)
        }
    }
}

if ($failures.Count -gt 0) {
    $message = @('Repository metadata validation failed:') + $failures
    throw ($message -join [Environment]::NewLine)
}

Write-Output ('Validated {0} agent metadata files and {1} skill files.' -f $agentFiles.Count, $skillFiles.Count)
