# diagnose_atlas_locks.ps1
# Reports which process(es) block a path under the Atlas install root.
# Run as Administrator for the most complete results.
param(
    [string]$AtlasRoot = "",
    [string]$TargetPath = ""
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $AtlasRoot) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $AtlasRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
}
if (-not $TargetPath) {
    $TargetPath = Join-Path $AtlasRoot "backend"
}

Write-Host "============================================================"
Write-Host " Atlas lock diagnostics"
Write-Host "------------------------------------------------------------"
Write-Host " Install root : $AtlasRoot"
Write-Host " Target path  : $TargetPath"
Write-Host "============================================================"
Write-Host ""

function Show-ProcessRow($p) {
    $cmd = $p.CommandLine
    if ($cmd.Length -gt 160) { $cmd = $cmd.Substring(0, 157) + "..." }
    Write-Host (" PID {0,-7} {1,-22} {2}" -f $p.ProcessId, $p.Name, $p.ExecutablePath)
    if ($cmd) { Write-Host "          CMD: $cmd" }
}

Write-Host "[1] Atlas-related processes (executable OR command line)"
$atlasProcs = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($AtlasRoot, [System.StringComparison]::OrdinalIgnoreCase)) -or
        ($_.CommandLine -and ($_.CommandLine -like "*$AtlasRoot*" -or $_.CommandLine -like "*apply_restart.bat*" -or $_.CommandLine -like "*release_atlas_locks.bat*"))
    }
if ($atlasProcs) {
    $atlasProcs | ForEach-Object { Show-ProcessRow $_ }
} else {
    Write-Host "  (none found by path/command line)"
}
Write-Host ""

Write-Host "[2] uvicorn / Atlas service suspects (any Python location)"
$uvicornProcs = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -match "uvicorn" -and (
                $_.CommandLine -match "server:app" -or
                $_.CommandLine -match "bridge_server:app"
            )
        )
    }
if ($uvicornProcs) {
    $uvicornProcs | ForEach-Object { Show-ProcessRow $_ }
} else {
    Write-Host "  (none found)"
}
Write-Host ""

Write-Host "[3] cmd.exe with Atlas scripts in command line"
$cmdProcs = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "cmd.exe" -and $_.CommandLine -and $_.CommandLine -like "*$AtlasRoot*" }
if ($cmdProcs) {
    $cmdProcs | ForEach-Object { Show-ProcessRow $_ }
} else {
    Write-Host "  (none found)"
}
Write-Host ""

Write-Host "[4] Windows services"
foreach ($svc in @("AtlasBackend", "AtlasBridge")) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s) {
        Write-Host "  $svc : $($s.Status)"
    } else {
        Write-Host "  $svc : (not registered)"
    }
}
Write-Host ""

Write-Host "[5] Directory lock probe"
$probe = Join-Path $TargetPath ".atlas_lock_probe"
$locked = $false
try {
    if (-not (Test-Path $TargetPath)) {
        Write-Host "  Target path does not exist."
    } else {
        New-Item -Path $probe -ItemType File -Force | Out-Null
        Remove-Item -Path $probe -Force
        try {
            $renamed = "$TargetPath.__atlas_rename_probe__"
            if (Test-Path $renamed) { Remove-Item $renamed -Recurse -Force }
            Rename-Item -Path $TargetPath -NewName (Split-Path $renamed -Leaf)
            Rename-Item -Path $renamed -NewName (Split-Path $TargetPath -Leaf)
            Write-Host "  Rename probe: OK (directory not locked)"
        } catch {
            $locked = $true
            Write-Host "  Rename probe: LOCKED — $($_.Exception.Message)"
        }
    }
} catch {
    $locked = $true
    Write-Host "  Write probe: LOCKED — $($_.Exception.Message)"
}
Write-Host ""

$handleExe = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "handle.exe"
if (-not (Test-Path $handleExe)) {
    $handleExe = "handle.exe"
}

if (Get-Command $handleExe -ErrorAction SilentlyContinue) {
    Write-Host "[6] Sysinternals handle.exe (definitive open-handle list)"
    & $handleExe -accepteula -nobanner $TargetPath 2>$null
} else {
    Write-Host "[6] Sysinternals handle.exe not found."
    Write-Host "    For a definitive answer, download handle.exe from Microsoft Sysinternals"
    Write-Host "    and run:  handle.exe -accepteula `"$TargetPath`""
    Write-Host "    Or use Resource Monitor → CPU tab → Associated Handles → search: backend"
}
Write-Host ""

if ($locked) {
    Write-Host "RESULT: $TargetPath appears LOCKED."
    Write-Host "Most common Atlas-specific causes:"
    Write-Host "  • cmd.exe still running apply_restart.bat (CWD = backend)"
    Write-Host "  • uvicorn/python started with system Python (not under install root)"
    Write-Host "  • File Explorer window open inside the folder"
    Write-Host "Run as admin:  scripts\release_atlas_locks.bat"
    exit 1
}

Write-Host "RESULT: No lock detected by rename/write probe."
exit 0
