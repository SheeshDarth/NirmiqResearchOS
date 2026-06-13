param(
    [switch]$OpenBrowser,
    [switch]$GoldenDemo
)

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "run_local.ps1"
$argsList = @()
if ($OpenBrowser) { $argsList += "-OpenBrowser" }
if ($GoldenDemo) { $argsList += "-GoldenDemo" }
& $script @argsList
