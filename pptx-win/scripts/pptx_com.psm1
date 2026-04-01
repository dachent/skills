Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ConvertTo-MsoTriState {
    param([bool]$Value)
    if ($Value) { return -1 }
    return 0
}

function ConvertTo-ObjectArray {
    param($InputObject)

    if ($null -eq $InputObject) {
        return ,([object[]]@())
    }

    if ($InputObject -is [System.Array]) {
        return ,([object[]]$InputObject)
    }

    if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
        $items = New-Object System.Collections.Generic.List[object]
        foreach ($item in $InputObject) {
            $items.Add($item)
        }
        return ,([object[]]$items.ToArray())
    }

    return ,([object[]]@($InputObject))
}

function Resolve-AbsolutePath {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [switch]$AllowMissing
    )

    if ($AllowMissing) {
        $parent = Split-Path -Parent $Path
        if ([string]::IsNullOrWhiteSpace($parent)) {
            $parent = (Get-Location).Path
        } elseif (-not [System.IO.Path]::IsPathRooted($parent)) {
            $parent = Join-Path (Get-Location).Path $parent
        }
        $leaf = Split-Path -Leaf $Path
        return [System.IO.Path]::GetFullPath((Join-Path $parent $leaf))
    }

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Path not found: $Path"
    }

    return (Resolve-Path -LiteralPath $Path).Path
}

function Get-TemporaryPptxWinRoot {
    $root = Join-Path ([System.IO.Path]::GetTempPath()) 'pptx-win'
    if (-not (Test-Path -LiteralPath $root)) {
        New-Item -ItemType Directory -Path $root -Force | Out-Null
    }
    return $root
}

function New-TemporaryPptxWinDirectory {
    param([string]$Prefix = 'pptxwin')

    $root = Get-TemporaryPptxWinRoot
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        $name = '{0}-{1}' -f $Prefix, ([guid]::NewGuid().ToString('N'))
        $path = Join-Path $root $name
        if (-not (Test-Path -LiteralPath $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
            return $path
        }
    }

    throw "Could not allocate a temporary pptx-win directory under '$root'."
}

function Test-WebUriPath {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    $uri = $null
    if (-not [System.Uri]::TryCreate($Path, [System.UriKind]::Absolute, [ref]$uri)) {
        return $false
    }

    return ($uri.Scheme -in @('http', 'https'))
}

function Test-EditablePowerPointOutputPath {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [int]$FileFormat = 24
    )

    if ($FileFormat -eq 24) {
        return $true
    }

    $editableExtensions = @(
        '.pptx', '.pptm', '.ppt', '.pot', '.potx', '.potm', '.pps', '.ppsx', '.ppsm'
    )
    $extension = [System.IO.Path]::GetExtension($Path)
    if ([string]::IsNullOrWhiteSpace($extension)) {
        return $false
    }

    return ($editableExtensions -contains $extension.ToLowerInvariant())
}

function Copy-OutputFileToDestination {
    param(
        [Parameter(Mandatory)] [string]$SourcePath,
        [Parameter(Mandatory)] [string]$DestinationPath
    )

    $resolvedSource = Resolve-AbsolutePath -Path $SourcePath
    $resolvedDestination = Resolve-AbsolutePath -Path $DestinationPath -AllowMissing
    $destinationParent = Split-Path -Parent $resolvedDestination
    if (-not (Test-Path -LiteralPath $destinationParent)) {
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    }

    try {
        Copy-Item -LiteralPath $resolvedSource -Destination $resolvedDestination -Force
    } catch {
        throw "PowerPoint saved a local file at '$resolvedSource', but the final copy to '$resolvedDestination' failed. $($_.Exception.Message)"
    }

    if (-not (Test-Path -LiteralPath $resolvedDestination)) {
        throw "PowerPoint saved a local file at '$resolvedSource', but the final copy to '$resolvedDestination' did not create the destination file."
    }

    return $resolvedDestination
}


function Convert-JsonObjectToHashtable {
    param([Parameter(Mandatory)] $InputObject)

    if ($null -eq $InputObject) {
        return $null
    }

    if (
        $InputObject -is [string] -or
        $InputObject -is [char] -or
        $InputObject -is [bool] -or
        $InputObject -is [ValueType]
    ) {
        return $InputObject
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        $result = @{}
        foreach ($key in $InputObject.Keys) {
            $result[[string]$key] = Convert-JsonObjectToHashtable -InputObject $InputObject[$key]
        }
        return $result
    }

    if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
        $items = @()
        foreach ($item in $InputObject) {
            $items += ,(Convert-JsonObjectToHashtable -InputObject $item)
        }
        return $items
    }

    $properties = @($InputObject.PSObject.Properties)
    if ($properties.Length -gt 0) {
        $result = @{}
        foreach ($property in $properties) {
            $result[[string]$property.Name] = Convert-JsonObjectToHashtable -InputObject $property.Value
        }
        return $result
    }

    return $InputObject
}

function Read-JsonFileAsHashtable {
    param([Parameter(Mandatory)] [string]$Path)

    $resolved = Resolve-AbsolutePath -Path $Path
    $raw = Get-Content -LiteralPath $resolved -Raw
    $jsonObject = ConvertFrom-Json -InputObject $raw
    $hashtable = Convert-JsonObjectToHashtable -InputObject $jsonObject
    if ($hashtable -isnot [System.Collections.IDictionary]) {
        throw 'Expected the JSON root value to be an object.'
    }
    return $hashtable
}

function New-PowerPointApplication {
    param([bool]$Visible = $false)

    $app = New-Object -ComObject PowerPoint.Application
    try {
        $app.Visible = (ConvertTo-MsoTriState -Value $Visible)
    } catch {
        # Some builds ignore or reject Visible changes; continue.
    }
    return $app
}

function Open-PowerPointPresentation {
    param(
        [Parameter(Mandatory)] $App,
        [Parameter(Mandatory)] [string]$Path,
        [bool]$ReadOnly = $true,
        [bool]$WithWindow = $false,
        [bool]$Untitled = $false
    )

    $fullPath = Resolve-AbsolutePath -Path $Path
    return $App.Presentations.Open(
        $fullPath,
        (ConvertTo-MsoTriState -Value $ReadOnly),
        (ConvertTo-MsoTriState -Value $Untitled),
        (ConvertTo-MsoTriState -Value $WithWindow)
    )
}

function New-PowerPointPresentation {
    param(
        [Parameter(Mandatory)] $App,
        [bool]$WithWindow = $false
    )

    return $App.Presentations.Add((ConvertTo-MsoTriState -Value $WithWindow))
}

function Close-PowerPointPresentation {
    param($Presentation)
    if ($null -ne $Presentation) {
        try {
            $Presentation.Close()
        } catch {
        }
    }
}

function Release-ComObject {
    param($ComObject)
    if ($null -ne $ComObject -and [System.Runtime.InteropServices.Marshal]::IsComObject($ComObject)) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($ComObject)
    }
}

function Stop-PowerPointApplication {
    param($App)
    if ($null -ne $App) {
        try {
            $App.Quit()
        } catch {
        }
        Release-ComObject -ComObject $App
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

function Save-PowerPointPresentation {
    param(
        [Parameter(Mandatory)] $Presentation,
        [Parameter(Mandatory)] [string]$Path,
        [int]$FileFormat = 24
    )

    $requestedPath = Resolve-AbsolutePath -Path $Path -AllowMissing
    $parent = Split-Path -Parent $requestedPath
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if (Test-EditablePowerPointOutputPath -Path $requestedPath -FileFormat $FileFormat) {
        $stagingDirectory = New-TemporaryPptxWinDirectory -Prefix 'presentation-save'
        $stagedPath = Join-Path $stagingDirectory (Split-Path -Leaf $requestedPath)

        $Presentation.SaveAs($stagedPath, $FileFormat)

        $presentationFullName = ''
        try {
            $presentationFullName = [string]$Presentation.FullName
        } catch {
        }

        if (Test-WebUriPath -Path $presentationFullName) {
            throw "PowerPoint rebound the presentation to cloud-backed path '$presentationFullName' while saving a staged editable copy at '$stagedPath'."
        }
        if (-not (Test-Path -LiteralPath $stagedPath)) {
            throw "PowerPoint did not create a local editable presentation output at '$stagedPath'."
        }

        return (Copy-OutputFileToDestination -SourcePath $stagedPath -DestinationPath $requestedPath)
    }

    $Presentation.SaveAs($requestedPath, $FileFormat)
    if (-not (Test-Path -LiteralPath $requestedPath)) {
        throw "PowerPoint output was not created at '$requestedPath'."
    }

    return $requestedPath
}

function Export-PowerPointPresentationSlides {
    param(
        [Parameter(Mandatory)] $Presentation,
        [Parameter(Mandatory)] [string]$OutputDir,
        [ValidateSet('PNG', 'JPG')] [string]$FilterName = 'PNG',
        [int]$Width = 1600,
        [int]$Height = 900
    )

    $fullOutputDir = Resolve-AbsolutePath -Path $OutputDir -AllowMissing
    if (-not (Test-Path -LiteralPath $fullOutputDir)) {
        New-Item -ItemType Directory -Path $fullOutputDir -Force | Out-Null
    }

    $Presentation.Export($fullOutputDir, $FilterName, $Width, $Height)

    $patterns = if ($FilterName -eq 'PNG') {
        @('Slide*.png')
    } else {
        @('Slide*.jpg', 'Slide*.jpeg')
    }
    $files = foreach ($pattern in $patterns) {
        Get-ChildItem -LiteralPath $fullOutputDir -Filter $pattern -ErrorAction SilentlyContinue
    }
    return ($files | Sort-Object FullName -Unique | Select-Object -ExpandProperty FullName)
}

function Get-TextFromShape {
    param($Shape)

    $texts = New-Object System.Collections.Generic.List[string]

    try {
        if ($Shape.HasTextFrame -ne 0 -and $Shape.TextFrame.HasText -ne 0) {
            $value = $Shape.TextFrame.TextRange.Text
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $texts.Add($value.Trim())
            }
        }
    } catch {
    }

    try {
        if ($Shape.HasTable -ne 0) {
            $rows = $Shape.Table.Rows.Count
            $cols = $Shape.Table.Columns.Count
            for ($r = 1; $r -le $rows; $r++) {
                for ($c = 1; $c -le $cols; $c++) {
                    try {
                        $cellText = $Shape.Table.Cell($r, $c).Shape.TextFrame.TextRange.Text
                        if (-not [string]::IsNullOrWhiteSpace($cellText)) {
                            $texts.Add($cellText.Trim())
                        }
                    } catch {
                    }
                }
            }
        }
    } catch {
    }

    try {
        $groupCount = $Shape.GroupItems.Count
        if ($groupCount -gt 0) {
            for ($i = 1; $i -le $groupCount; $i++) {
                foreach ($childText in (Get-TextFromShape -Shape $Shape.GroupItems.Item($i))) {
                    if (-not [string]::IsNullOrWhiteSpace($childText)) {
                        $texts.Add($childText)
                    }
                }
            }
        }
    } catch {
    }

    return (ConvertTo-ObjectArray -InputObject $texts)
}

function Get-NotesTextFromSlide {
    param($Slide)

    $texts = New-Object System.Collections.Generic.List[string]
    try {
        foreach ($shape in (Get-UserNotesPageShapes -Slide $Slide)) {
            foreach ($value in (Get-TextFromShape -Shape $shape)) {
                if (-not [string]::IsNullOrWhiteSpace($value)) {
                    $texts.Add($value)
                }
            }
        }
    } catch {
    }
    return (($texts | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) | Select-Object -Unique)
}

function Get-UserNotesPageShapes {
    param($Slide)

    $shapes = New-Object System.Collections.Generic.List[object]
    try {
        $notesShapes = $Slide.NotesPage.Shapes
        for ($i = 1; $i -le $notesShapes.Count; $i++) {
            $shape = $notesShapes.Item($i)

            $hasUserText = $false
            try {
                $hasUserText = ($shape.HasTextFrame -ne 0 -and $shape.TextFrame.HasText -ne 0)
            } catch {
            }
            if (-not $hasUserText) {
                continue
            }

            $placeholderType = $null
            try {
                $placeholderType = [int]$shape.PlaceholderFormat.Type
            } catch {
            }

            # Keep the notes body placeholder and custom text boxes, but exclude built-in slide image/number/footer placeholders.
            if ($null -ne $placeholderType -and $placeholderType -notin @(0, 2)) {
                continue
            }

            $shapes.Add($shape)
        }
    } catch {
    }

    return (ConvertTo-ObjectArray -InputObject $shapes)
}

function Get-ShapeInventoryForSlide {
    param($Slide)

    $items = New-Object System.Collections.Generic.List[object]
    for ($i = 1; $i -le $Slide.Shapes.Count; $i++) {
        $shape = $Slide.Shapes.Item($i)
        $shapeTexts = @(Get-TextFromShape -Shape $shape)
        $item = [ordered]@{
            index = $i
            name = $shape.Name
            type = $shape.Type
            left = [Math]::Round([double]$shape.Left, 2)
            top = [Math]::Round([double]$shape.Top, 2)
            width = [Math]::Round([double]$shape.Width, 2)
            height = [Math]::Round([double]$shape.Height, 2)
            text = ($shapeTexts -join "`n")
        }
        $items.Add([pscustomobject]$item)
    }
    return (ConvertTo-ObjectArray -InputObject $items)
}

function Get-PowerPointPresentationReport {
    param(
        [Parameter(Mandatory)] $Presentation,
        [bool]$IncludeNotes = $true,
        [bool]$IncludeShapeInventory = $false,
        [string]$SourcePath = ''
    )

    $slides = New-Object System.Collections.Generic.List[object]
    for ($index = 1; $index -le $Presentation.Slides.Count; $index++) {
        $slide = $Presentation.Slides.Item($index)
        $textBlocks = New-Object System.Collections.Generic.List[string]
        $title = ''

        for ($shapeIndex = 1; $shapeIndex -le $slide.Shapes.Count; $shapeIndex++) {
            $shape = $slide.Shapes.Item($shapeIndex)
            foreach ($textValue in (Get-TextFromShape -Shape $shape)) {
                if (-not [string]::IsNullOrWhiteSpace($textValue)) {
                    $textBlocks.Add($textValue)
                }
            }
            if ([string]::IsNullOrWhiteSpace($title)) {
                try {
                    if ($shape.HasTextFrame -ne 0 -and $shape.TextFrame.HasText -ne 0) {
                        $candidate = $shape.TextFrame.TextRange.Text.Trim()
                        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
                            $title = $candidate
                        }
                    }
                } catch {
                }
            }
        }

        $slideObject = [ordered]@{
            index = $index
            slide_id = $slide.SlideID
            hidden = [bool]($slide.SlideShowTransition.Hidden -ne 0)
            title = $title
            text = @($textBlocks | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        }

        if ($IncludeNotes) {
            $slideObject.notes = @(Get-NotesTextFromSlide -Slide $slide)
        }
        if ($IncludeShapeInventory) {
            $slideObject.shapes = @(Get-ShapeInventoryForSlide -Slide $slide)
        }

        $slides.Add([pscustomobject]$slideObject)
    }

    $pageSetup = $Presentation.PageSetup
    return [pscustomobject]([ordered]@{
        source_path = $SourcePath
        slide_count = $Presentation.Slides.Count
        slide_width_points = [Math]::Round([double]$pageSetup.SlideWidth, 2)
        slide_height_points = [Math]::Round([double]$pageSetup.SlideHeight, 2)
        slide_width_inches = [Math]::Round(([double]$pageSetup.SlideWidth / 72.0), 3)
        slide_height_inches = [Math]::Round(([double]$pageSetup.SlideHeight / 72.0), 3)
        slides = (ConvertTo-ObjectArray -InputObject $slides)
    })
}

function Convert-PresentationReportToMarkdown {
    param([Parameter(Mandatory)] $Report)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('# Presentation Report')
    $lines.Add('')
    if ($Report.source_path) {
        $lines.Add("- Source: $($Report.source_path)")
    }
    $lines.Add("- Slide count: $($Report.slide_count)")
    $lines.Add("- Size (inches): $($Report.slide_width_inches) x $($Report.slide_height_inches)")
    $lines.Add('')

    foreach ($slide in $Report.slides) {
        $textEntries = ConvertTo-ObjectArray -InputObject $slide.text
        $notesProperty = $slide.PSObject.Properties['notes']
        $shapeProperty = $slide.PSObject.Properties['shapes']
        $notesEntries = if ($null -ne $notesProperty) {
            ConvertTo-ObjectArray -InputObject $notesProperty.Value
        } else {
            @()
        }
        $shapeEntries = if ($null -ne $shapeProperty) {
            ConvertTo-ObjectArray -InputObject $shapeProperty.Value
        } else {
            @()
        }

        $heading = "## Slide $($slide.index)"
        if (-not [string]::IsNullOrWhiteSpace($slide.title)) {
            $heading = "$heading - $($slide.title)"
        }
        $lines.Add($heading)
        $lines.Add('')
        $lines.Add("- Hidden: $($slide.hidden)")
        $addedTextHeader = $false
        foreach ($textEntry in $textEntries) {
            if (-not $addedTextHeader) {
                $lines.Add('- Text:')
                $addedTextHeader = $true
            }
            $singleLine = ($textEntry -replace "`r?`n", ' / ')
            $lines.Add("  - $singleLine")
        }
        $addedNotesHeader = $false
        foreach ($noteEntry in $notesEntries) {
            if (-not $addedNotesHeader) {
                $lines.Add('- Notes:')
                $addedNotesHeader = $true
            }
            $singleLine = ($noteEntry -replace "`r?`n", ' / ')
            $lines.Add("  - $singleLine")
        }
        $addedShapesHeader = $false
        foreach ($shape in $shapeEntries) {
            if (-not $addedShapesHeader) {
                $lines.Add('- Shapes:')
                $addedShapesHeader = $true
            }
            $shapeText = $shape.text
            if ([string]::IsNullOrWhiteSpace($shapeText)) {
                $shapeText = ''
            } else {
                $shapeText = " - " + ($shapeText -replace "`r?`n", ' / ')
            }
            $lines.Add("  - [$($shape.index)] $($shape.name) type=$($shape.type) x=$($shape.left) y=$($shape.top) w=$($shape.width) h=$($shape.height)$shapeText")
        }
        $lines.Add('')
    }

    return ($lines -join "`r`n")
}

function Invoke-LiteralReplacement {
    param(
        [Parameter(Mandatory)] [string]$Text,
        [Parameter(Mandatory)] [hashtable]$Map
    )

    $updated = $Text
    foreach ($key in $Map.Keys) {
        $replacement = [string]$Map[$key]
        $updated = $updated.Replace([string]$key, $replacement)
    }
    return $updated
}

function Set-TextOnShape {
    param(
        [Parameter(Mandatory)] $Shape,
        [Parameter(Mandatory)] [hashtable]$Map
    )

    $changes = 0

    try {
        if ($Shape.HasTextFrame -ne 0 -and $Shape.TextFrame.HasText -ne 0) {
            $original = [string]$Shape.TextFrame.TextRange.Text
            $updated = Invoke-LiteralReplacement -Text $original -Map $Map
            if ($updated -ne $original) {
                $Shape.TextFrame.TextRange.Text = $updated
                $changes++
            }
        }
    } catch {
    }

    try {
        if ($Shape.HasTable -ne 0) {
            $rows = $Shape.Table.Rows.Count
            $cols = $Shape.Table.Columns.Count
            for ($r = 1; $r -le $rows; $r++) {
                for ($c = 1; $c -le $cols; $c++) {
                    try {
                        $cellRange = $Shape.Table.Cell($r, $c).Shape.TextFrame.TextRange
                        $original = [string]$cellRange.Text
                        $updated = Invoke-LiteralReplacement -Text $original -Map $Map
                        if ($updated -ne $original) {
                            $cellRange.Text = $updated
                            $changes++
                        }
                    } catch {
                    }
                }
            }
        }
    } catch {
    }

    try {
        $groupCount = $Shape.GroupItems.Count
        if ($groupCount -gt 0) {
            for ($i = 1; $i -le $groupCount; $i++) {
                $changes += Set-TextOnShape -Shape $Shape.GroupItems.Item($i) -Map $Map
            }
        }
    } catch {
    }

    return $changes
}

function Replace-TextInPowerPointPresentation {
    param(
        [Parameter(Mandatory)] $Presentation,
        [Parameter(Mandatory)] [hashtable]$Map,
        [bool]$IncludeNotes = $true
    )

    $changes = 0
    for ($slideIndex = 1; $slideIndex -le $Presentation.Slides.Count; $slideIndex++) {
        $slide = $Presentation.Slides.Item($slideIndex)
        for ($shapeIndex = 1; $shapeIndex -le $slide.Shapes.Count; $shapeIndex++) {
            $changes += Set-TextOnShape -Shape $slide.Shapes.Item($shapeIndex) -Map $Map
        }

        if ($IncludeNotes) {
            try {
                foreach ($notesShape in (Get-UserNotesPageShapes -Slide $slide)) {
                    $changes += Set-TextOnShape -Shape $notesShape -Map $Map
                }
            } catch {
            }
        }
    }

    return $changes
}

Export-ModuleMember -Function ConvertTo-MsoTriState
Export-ModuleMember -Function ConvertTo-ObjectArray
Export-ModuleMember -Function Convert-JsonObjectToHashtable
Export-ModuleMember -Function Read-JsonFileAsHashtable
Export-ModuleMember -Function Resolve-AbsolutePath
Export-ModuleMember -Function New-PowerPointApplication
Export-ModuleMember -Function Open-PowerPointPresentation
Export-ModuleMember -Function New-PowerPointPresentation
Export-ModuleMember -Function Close-PowerPointPresentation
Export-ModuleMember -Function Stop-PowerPointApplication
Export-ModuleMember -Function Save-PowerPointPresentation
Export-ModuleMember -Function Export-PowerPointPresentationSlides
Export-ModuleMember -Function Get-PowerPointPresentationReport
Export-ModuleMember -Function Convert-PresentationReportToMarkdown
Export-ModuleMember -Function Replace-TextInPowerPointPresentation
