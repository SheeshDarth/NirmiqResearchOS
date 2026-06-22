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
$desktopLauncher = Join-Path $root "NIRMIQ Desktop.cmd"
$goldenLauncher = Join-Path $root "NIRMIQ Golden Demo.cmd"
$stopper = Join-Path $root "NIRMIQ Stop.cmd"
$icon = Join-Path $env:SystemRoot "System32\shell32.dll"

if (-not (Test-Path $launcher)) {
    throw "Launcher not found: $launcher"
}

if (-not (Test-Path $desktopLauncher)) {
    throw "Desktop launcher not found: $desktopLauncher"
}

if (-not (Test-Path $goldenLauncher)) {
    throw "Golden demo launcher not found: $goldenLauncher"
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
        -ShortcutPath (Join-Path $desktopPath "NIRMIQ Desktop.lnk") `
        -TargetPath $desktopLauncher `
        -Description "Launch NIRMIQ ResearchOS desktop app" `
        -IconIndex 13
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $desktopPath "NIRMIQ Browser Preview.lnk") `
        -TargetPath $launcher `
        -Description "Launch NIRMIQ ResearchOS browser preview" `
        -IconIndex 13
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $desktopPath "NIRMIQ Golden Demo.lnk") `
        -TargetPath $goldenLauncher `
        -Description "Launch NIRMIQ ResearchOS with the golden demo corpus" `
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
        -ShortcutPath (Join-Path $startMenuPath "NIRMIQ Desktop.lnk") `
        -TargetPath $desktopLauncher `
        -Description "Launch NIRMIQ ResearchOS desktop app" `
        -IconIndex 13
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $startMenuPath "NIRMIQ Browser Preview.lnk") `
        -TargetPath $launcher `
        -Description "Launch NIRMIQ ResearchOS browser preview" `
        -IconIndex 13
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $startMenuPath "NIRMIQ Golden Demo.lnk") `
        -TargetPath $goldenLauncher `
        -Description "Launch NIRMIQ ResearchOS with the golden demo corpus" `
        -IconIndex 13
    New-NirmiqShortcut `
        -ShortcutPath (Join-Path $startMenuPath "Stop NIRMIQ ResearchOS.lnk") `
        -TargetPath $stopper `
        -Description "Stop NIRMIQ ResearchOS local preview services" `
        -IconIndex 28
}
