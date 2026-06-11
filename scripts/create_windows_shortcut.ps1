param(
    [switch]$Desktop,
    [switch]$StartMenu
)

$ErrorActionPreference = "Stop"

if (-not $Desktop -and -not $StartMenu) {
    $Desktop = $true
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$launcher = Join-Path $root "NIRMIQ ResearchOS.cmd"
$stopper = Join-Path $root "NIRMIQ Stop.cmd"
$icon = Join-Path $env:SystemRoot "System32\shell32.dll"

if (-not (Test-Path $launcher)) {
    throw "Launcher not found: $launcher"
}

function New-NirmiqShortcut {
    param(
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$Description,
        [int]$IconIndex
    )
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = [string]$root
    $shortcut.Description = $Description
    $shortcut.IconLocation = "$icon,$IconIndex"
    $shortcut.Save()
    Write-Output "Created shortcut: $ShortcutPath"
}

if ($Desktop) {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $desktopPath "NIRMIQ ResearchOS.lnk") `
        -TargetPath $launcher `
        -Description "Launch NIRMIQ ResearchOS local academic intelligence workspace" `
        -IconIndex 13
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $desktopPath "Stop NIRMIQ ResearchOS.lnk") `
        -TargetPath $stopper `
        -Description "Stop NIRMIQ ResearchOS local preview services" `
        -IconIndex 28
}

if ($StartMenu) {
    $startMenuPath = Join-Path ([Environment]::GetFolderPath("Programs")) "NIRMIQ"
    New-Item -ItemType Directory -Force -Path $startMenuPath | Out-Null
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $startMenuPath "NIRMIQ ResearchOS.lnk") `
        -TargetPath $launcher `
        -Description "Launch NIRMIQ ResearchOS local academic intelligence workspace" `
        -IconIndex 13
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $startMenuPath "Stop NIRMIQ ResearchOS.lnk") `
        -TargetPath $stopper `
        -Description "Stop NIRMIQ ResearchOS local preview services" `
        -IconIndex 28
}
