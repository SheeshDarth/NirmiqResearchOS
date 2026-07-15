param(
    [switch]$OpenBrowser,
    [switch]$GoldenDemo,
    [switch]$SkipDoctor
)

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "run_local.ps1"
$argsList = @()
if ($OpenBrowser) { $argsList += "-OpenBrowser" }
if ($GoldenDemo) { $argsList += "-GoldenDemo" }
if ($SkipDoctor) { $argsList += "-SkipDoctor" }
& $script @argsList
