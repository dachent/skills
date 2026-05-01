Set-StrictMode -Version Latest

function Get-CurrentUserName {
    try {
        $name = (whoami).Trim()
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            return $name
        }
    }
    catch {
    }

    return [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
}

function Test-IsSandboxUser {
    param(
        [Parameter(Mandatory)]
        [string]$UserName
    )

    return ($UserName -match '(?i)codexsandbox')
}

function Get-CurrentSessionId {
    return [System.Diagnostics.Process]::GetCurrentProcess().SessionId
}

function Get-SessionStateInfo {
    param(
        [Parameter(Mandatory)]
        [int]$SessionId
    )

    try {
        $rawOutput = (& query session 2>&1 | Out-String)
    }
    catch {
        return [pscustomobject]@{
            state = 'Unknown'
            ok = $false
            message = "Could not query Windows session state. $($_.Exception.Message)"
        }
    }

    $state = $null
    foreach ($line in ($rawOutput -split "`r?`n")) {
        if ($line -match "(?:^|\s)$SessionId\s+(?<state>Active|Conn|Disc|Down|Init|Listen|Reset)\b") {
            $state = $Matches['state']
            break
        }
    }

    if ([string]::IsNullOrWhiteSpace($state)) {
        return [pscustomobject]@{
            state = 'Unknown'
            ok = $false
            message = "Could not determine the state of Windows session $SessionId."
        }
    }

    return [pscustomobject]@{
        state = $state
        ok = $true
        message = "Windows session $SessionId is $state."
    }
}

function Initialize-InputDesktopProbeType {
    $existingType = [System.Management.Automation.PSTypeName]'CodexOfficeDesktopProbe'
    if ($null -ne $existingType.Type) {
        return
    }

    Add-Type -TypeDefinition @"
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

public static class CodexOfficeDesktopProbe
{
    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr OpenInputDesktop(uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool CloseDesktop(IntPtr hDesktop);

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool GetUserObjectInformation(
        IntPtr hObj,
        int nIndex,
        StringBuilder pvInfo,
        int nLength,
        ref int lpnLengthNeeded
    );

    private const uint DESKTOP_READOBJECTS = 0x0001;
    private const uint DESKTOP_SWITCHDESKTOP = 0x0100;
    private const int UOI_NAME = 2;

    public static string GetInputDesktopName()
    {
        IntPtr desktopHandle = OpenInputDesktop(0, false, DESKTOP_READOBJECTS | DESKTOP_SWITCHDESKTOP);
        if (desktopHandle == IntPtr.Zero)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }

        try
        {
            int lengthNeeded = 0;
            var builder = new StringBuilder(512);
            if (!GetUserObjectInformation(desktopHandle, UOI_NAME, builder, builder.Capacity, ref lengthNeeded))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }

            return builder.ToString();
        }
        finally
        {
            CloseDesktop(desktopHandle);
        }
    }
}
"@
}

function Get-InputDesktopInfo {
    try {
        Initialize-InputDesktopProbeType
        $desktopName = [CodexOfficeDesktopProbe]::GetInputDesktopName()
        if ([string]::IsNullOrWhiteSpace($desktopName)) {
            return [pscustomobject]@{
                state = 'Unknown'
                ok = $false
                is_locked = $false
                message = 'The Windows input desktop name was empty.'
            }
        }

        return [pscustomobject]@{
            state = $desktopName
            ok = $true
            is_locked = ($desktopName -ne 'Default')
            message = "Windows input desktop is '$desktopName'."
        }
    }
    catch {
        return [pscustomobject]@{
            state = 'Unknown'
            ok = $false
            is_locked = $false
            message = "Could not determine the Windows input desktop state. $($_.Exception.Message)"
        }
    }
}

function Get-RequestedOfficeApps {
    param(
        [string[]]$Apps
    )

    if ($null -eq $Apps -or $Apps.Count -eq 0) {
        return @('Excel', 'PowerPoint', 'Word')
    }

    $items = New-Object System.Collections.Generic.List[string]
    foreach ($app in $Apps) {
        if ([string]::IsNullOrWhiteSpace($app)) {
            continue
        }

        switch ($app.Trim().ToLowerInvariant()) {
            'excel' { $normalized = 'Excel' }
            'powerpoint' { $normalized = 'PowerPoint' }
            'word' { $normalized = 'Word' }
            default { throw "Unsupported Office app: $app" }
        }

        if (-not $items.Contains($normalized)) {
            $items.Add($normalized)
        }
    }

    if ($items.Count -eq 0) {
        return @('Excel', 'PowerPoint', 'Word')
    }

    return @($items.ToArray())
}

function Get-OfficeProgId {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string]$AppName
    )

    switch ($AppName) {
        'Excel' { return 'Excel.Application' }
        'PowerPoint' { return 'PowerPoint.Application' }
        'Word' { return 'Word.Application' }
        default { throw "Unsupported Office app: $AppName" }
    }
}

function Get-SkippedOfficeProbe {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string]$AppName
    )

    return [pscustomobject]@{
        app = $AppName
        prog_id = (Get-OfficeProgId -AppName $AppName)
        ok = $null
        skipped = $true
        error_kind = $null
        message = "$AppName COM probe was not requested."
        raw_message = $null
    }
}

function Get-OfficeComErrorInfo {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string]$AppName,

        [Parameter(Mandatory)]
        [string]$RawMessage
    )

    $normalized = $RawMessage.ToLowerInvariant()
    $errorKind = 'runtime_error'
    $message = "$AppName COM probe failed. $RawMessage"

    if (
        $normalized.Contains('0x80070520') -or
        $normalized.Contains('80070520') -or
        $normalized.Contains('specified logon session does not exist') -or
        $normalized.Contains('retrieving the com class factory')
    ) {
        $errorKind = 'office_com_wrong_session'
        $message = "$AppName COM is unavailable in this shell. Run Office COM from a regular PowerShell window opened as the signed-in desktop user."
    }
    elseif (
        $normalized.Contains('class not registered') -or
        $normalized.Contains('activex component can''t create object')
    ) {
        $errorKind = 'office_not_installed'
        $message = "$AppName desktop COM could not be created. Confirm that Microsoft 365 $AppName desktop is installed and registered."
    }
    elseif (
        $normalized.Contains('call was rejected by callee') -or
        $normalized.Contains('application is busy') -or
        $normalized.Contains('message filter indicated that the application is busy')
    ) {
        $errorKind = 'office_busy'
        $message = "$AppName is busy and did not accept the COM call. Close blocking dialogs and retry."
    }

    return [pscustomobject]@{
        error_kind = $errorKind
        message = $message
        raw_message = $RawMessage
    }
}

function Invoke-OfficeComProbe {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string]$AppName
    )

    $progId = Get-OfficeProgId -AppName $AppName
    $app = $null

    try {
        $app = New-Object -ComObject $progId

        switch ($AppName) {
            'Excel' {
                $app.Visible = $false
                $app.DisplayAlerts = $false
            }
            'PowerPoint' {
                try {
                    $app.Visible = 0
                }
                catch {
                }
            }
            'Word' {
                $app.Visible = $false
                $app.DisplayAlerts = 0
            }
        }

        return [pscustomobject]@{
            app = $AppName
            prog_id = $progId
            ok = $true
            skipped = $false
            error_kind = $null
            message = "$AppName COM probe succeeded."
            raw_message = $null
        }
    }
    catch {
        $info = Get-OfficeComErrorInfo -AppName $AppName -RawMessage $_.Exception.Message
        return [pscustomobject]@{
            app = $AppName
            prog_id = $progId
            ok = $false
            skipped = $false
            error_kind = $info.error_kind
            message = $info.message
            raw_message = $info.raw_message
        }
    }
    finally {
        if ($null -ne $app) {
            try {
                $app.Quit()
            }
            catch {
            }

            try {
                [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
            }
            catch {
            }

            [GC]::Collect()
            [GC]::WaitForPendingFinalizers()
        }
    }
}

function Get-RelevantOfficeProbe {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Preflight,

        [Parameter(Mandatory)]
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string]$AppName
    )

    switch ($AppName) {
        'Excel' { return $Preflight.excel_probe }
        'PowerPoint' { return $Preflight.powerpoint_probe }
        'Word' { return $Preflight.word_probe }
        default { throw "Unsupported Office app: $AppName" }
    }
}

function Get-OfficePreflightFailureInfo {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Preflight,

        [Parameter(Mandatory)]
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string]$AppName
    )

    if ($Preflight.is_sandbox_user) {
        return [pscustomobject]@{
            error_kind = 'office_com_sandbox_user'
            message = $Preflight.reason
        }
    }

    if ($Preflight.session_state -ne 'Active' -or $Preflight.desktop_state -ne 'Default') {
        return [pscustomobject]@{
            error_kind = 'interactive_session_required'
            message = $Preflight.reason
        }
    }

    $probe = Get-RelevantOfficeProbe -Preflight $Preflight -AppName $AppName
    if ($null -ne $probe -and $probe.ok -ne $true) {
        return [pscustomobject]@{
            error_kind = if ([string]::IsNullOrWhiteSpace([string]$probe.error_kind)) { 'office_com_unavailable' } else { [string]$probe.error_kind }
            message = $probe.message
        }
    }

    return $null
}

function Get-OfficeComPreflightResult {
    param(
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string[]]$Apps = @('Excel', 'PowerPoint', 'Word')
    )

    $requestedApps = Get-RequestedOfficeApps -Apps $Apps
    $currentUser = Get-CurrentUserName
    $sessionId = Get-CurrentSessionId
    $sessionInfo = Get-SessionStateInfo -SessionId $sessionId
    $desktopInfo = Get-InputDesktopInfo
    $isSandboxUser = Test-IsSandboxUser -UserName $currentUser

    $excelProbe = if ($requestedApps -contains 'Excel') { Invoke-OfficeComProbe -AppName 'Excel' } else { Get-SkippedOfficeProbe -AppName 'Excel' }
    $powerPointProbe = if ($requestedApps -contains 'PowerPoint') { Invoke-OfficeComProbe -AppName 'PowerPoint' } else { Get-SkippedOfficeProbe -AppName 'PowerPoint' }
    $wordProbe = if ($requestedApps -contains 'Word') { Invoke-OfficeComProbe -AppName 'Word' } else { Get-SkippedOfficeProbe -AppName 'Word' }

    $requestedProbes = @()
    foreach ($appName in $requestedApps) {
        $requestedProbes += @(Get-RelevantOfficeProbe -Preflight ([pscustomobject]@{
                    excel_probe = $excelProbe
                    powerpoint_probe = $powerPointProbe
                    word_probe = $wordProbe
                }) -AppName $appName)
    }

    $reason = if ($isSandboxUser) {
        'The current shell is the Codex sandbox user. Office COM must run from a regular PowerShell window opened as the signed-in desktop user.'
    }
    elseif ($sessionInfo.state -ne 'Active') {
        "Windows session $sessionId is $($sessionInfo.state), not Active. Office COM requires an active interactive desktop session."
    }
    elseif (-not $desktopInfo.ok) {
        $desktopInfo.message
    }
    elseif ($desktopInfo.state -ne 'Default') {
        "Windows input desktop is '$($desktopInfo.state)', not 'Default'. Office COM requires the unlocked interactive desktop."
    }
    else {
        $failingProbe = $requestedProbes | Where-Object { $_.ok -ne $true } | Select-Object -First 1
        if ($null -ne $failingProbe) {
            $failingProbe.message
        }
        else {
            'Office COM is available in the current desktop user session.'
        }
    }

    $canUseCom = (-not $isSandboxUser) -and ($sessionInfo.state -eq 'Active') -and $desktopInfo.ok -and ($desktopInfo.state -eq 'Default') -and ($null -eq ($requestedProbes | Where-Object { $_.ok -ne $true } | Select-Object -First 1))

    return [pscustomobject]@{
        requested_apps = @($requestedApps)
        can_use_com = $canUseCom
        reason = $reason
        current_user = $currentUser
        session_id = $sessionId
        session_state = $sessionInfo.state
        desktop_state = $desktopInfo.state
        is_input_desktop_locked = $desktopInfo.is_locked
        is_sandbox_user = $isSandboxUser
        excel_probe = $excelProbe
        powerpoint_probe = $powerPointProbe
        word_probe = $wordProbe
    }
}

function Assert-OfficeComAvailable {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Excel', 'PowerPoint', 'Word')]
        [string]$AppName,

        [pscustomobject]$Preflight
    )

    if ($null -eq $Preflight) {
        $Preflight = Get-OfficeComPreflightResult -Apps @($AppName)
    }

    $failureInfo = Get-OfficePreflightFailureInfo -Preflight $Preflight -AppName $AppName
    if ($null -ne $failureInfo) {
        throw $failureInfo.message
    }

    return $Preflight
}

function Get-OfficePowerShellExecutable {
    $pwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pwshCommand -and -not [string]::IsNullOrWhiteSpace($pwshCommand.Source)) {
        return $pwshCommand.Source
    }

    $powershellCommand = Get-Command powershell -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $powershellCommand -and -not [string]::IsNullOrWhiteSpace($powershellCommand.Source)) {
        return $powershellCommand.Source
    }

    throw 'Could not find pwsh.exe or powershell.exe.'
}

function Try-ParseJson {
    param(
        [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    $trimmed = $Text.Trim()
    if (-not ($trimmed.StartsWith('{') -or $trimmed.StartsWith('['))) {
        return $null
    }

    try {
        return ($trimmed | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function Invoke-ChildPowerShellScript {
    param(
        [Parameter(Mandatory)]
        [string]$ScriptPath,

        [string[]]$ScriptArguments = @()
    )

    $powershellExe = Get-OfficePowerShellExecutable
    if ($null -eq $ScriptArguments) {
        $ScriptArguments = @()
    }
    $output = & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @ScriptArguments 2>&1 | Out-String

    return [pscustomobject]@{
        executable = $powershellExe
        script_path = $ScriptPath
        script_arguments = @($ScriptArguments)
        exit_code = $LASTEXITCODE
        output = $output.Trim()
        parsed_output = Try-ParseJson -Text $output
    }
}

Export-ModuleMember -Function Get-CurrentUserName
Export-ModuleMember -Function Test-IsSandboxUser
Export-ModuleMember -Function Get-CurrentSessionId
Export-ModuleMember -Function Get-SessionStateInfo
Export-ModuleMember -Function Get-InputDesktopInfo
Export-ModuleMember -Function Get-OfficeComErrorInfo
Export-ModuleMember -Function Invoke-OfficeComProbe
Export-ModuleMember -Function Get-RequestedOfficeApps
Export-ModuleMember -Function Get-RelevantOfficeProbe
Export-ModuleMember -Function Get-OfficePreflightFailureInfo
Export-ModuleMember -Function Get-OfficeComPreflightResult
Export-ModuleMember -Function Assert-OfficeComAvailable
Export-ModuleMember -Function Get-OfficePowerShellExecutable
Export-ModuleMember -Function Try-ParseJson
Export-ModuleMember -Function Invoke-ChildPowerShellScript
