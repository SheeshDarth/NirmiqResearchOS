param(
    [switch]$Portable
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$desktopDir = Join-Path $root "apps\desktop"
$builderCache = Join-Path $root "temp\electron-builder-cache"

New-Item -ItemType Directory -Force -Path $builderCache | Out-Null
$env:ELECTRON_BUILDER_CACHE = $builderCache

$npm = (Get-Command npm.cmd -ErrorAction Stop).Source

if ($Portable) {
    & $npm --prefix $desktopDir run package
} else {
    & $npm --prefix $desktopDir run pack
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
