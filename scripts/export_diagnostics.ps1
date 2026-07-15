param(
    [string]$OutputDirectory = "",
    [switch]$OpenFolder,
    [switch]$KeepExpandedFolder
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$userHome = [Environment]::GetFolderPath("UserProfile")
$outputRoot = if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    Join-Path $root "temp\diagnostics"
} elseif ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
}

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$bundleName = "nirmiq-safe-diagnostics-$timestamp"
$stagingRoot = Join-Path $outputRoot "$bundleName-$([guid]::NewGuid().ToString('N'))"
$archivePath = Join-Path $outputRoot "$bundleName.zip"

function Redact-DiagnosticText {
    param([string]$Value)

    $text = [string]$Value
    foreach ($sensitivePath in @($root, $userHome)) {
        if ([string]::IsNullOrWhiteSpace($sensitivePath)) {
            continue
        }
        $escaped = [regex]::Escape($sensitivePath.TrimEnd("\", "/"))
        $pathPattern = $escaped + '(?:[\\/][^\r\n"''<>|]*)?'
        $text = [regex]::Replace(
            $text,
            $pathPattern,
            "<local-path>",
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
        )
    }
    $text = [regex]::Replace($text, '[A-Za-z]:\\[^\r\n"''<>|]*', '<local-path>')
    $text = [regex]::Replace($text, 'file:///[^\s)]+', '<local-file>')
    $text = [regex]::Replace($text, '/(?:home|Users)/[^\s"''<>]+', '<local-path>')
    return $text
}

function Get-VersionText {
    param(
        [string]$Command,
        [string[]]$Arguments
    )
    try {
        $output = (& $Command @Arguments 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
            return "unavailable"
        }
        return (Redact-DiagnosticText $output)
    } catch {
        return "unavailable"
    }
}

function Test-LocalPort {
    param([int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-GitValue {
    param([string[]]$Arguments)
    try {
        $value = (& git -C $root @Arguments 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $value) {
            return (Redact-DiagnosticText $value)
        }
    } catch {
        return "unavailable"
    }
    return "unavailable"
}

function Get-RuntimeLogSummary {
    $categories = @{
        api = [ordered]@{ category = "api"; file_count = 0; total_bytes = 0L; last_modified_utc = $null; error_markers = 0; warning_markers = 0; failure_markers = 0 }
        web = [ordered]@{ category = "web"; file_count = 0; total_bytes = 0L; last_modified_utc = $null; error_markers = 0; warning_markers = 0; failure_markers = 0 }
        desktop = [ordered]@{ category = "desktop"; file_count = 0; total_bytes = 0L; last_modified_utc = $null; error_markers = 0; warning_markers = 0; failure_markers = 0 }
        other = [ordered]@{ category = "other-runtime"; file_count = 0; total_bytes = 0L; last_modified_utc = $null; error_markers = 0; warning_markers = 0; failure_markers = 0 }
    }
    $logDirectories = @(
        (Join-Path $root "temp\runtime"),
        (Join-Path $root "temp\desktop")
    )

    foreach ($directory in $logDirectories) {
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
            continue
        }
        foreach ($file in Get-ChildItem -LiteralPath $directory -Filter "*.log" -File -ErrorAction SilentlyContinue) {
            $name = $file.Name.ToLowerInvariant()
            $category = if ($name.StartsWith("api")) { "api" } elseif ($name.StartsWith("web")) { "web" } elseif ($name.StartsWith("desktop")) { "desktop" } else { "other" }
            $entry = $categories[$category]
            $entry["file_count"] = [int]$entry["file_count"] + 1
            $entry["total_bytes"] = [long]$entry["total_bytes"] + [long]$file.Length
            $modified = $file.LastWriteTimeUtc.ToString("o")
            if (-not $entry["last_modified_utc"] -or $modified -gt [string]$entry["last_modified_utc"]) {
                $entry["last_modified_utc"] = $modified
            }

            # Inspect only for aggregate markers. Raw lines never leave process memory.
            $tail = (Get-Content -LiteralPath $file.FullName -Tail 1500 -ErrorAction SilentlyContinue | Out-String)
            $entry["error_markers"] = [int]$entry["error_markers"] + [regex]::Matches($tail, '(?i)\b(error|exception|traceback)\b').Count
            $entry["warning_markers"] = [int]$entry["warning_markers"] + [regex]::Matches($tail, '(?i)\bwarn(?:ing)?\b').Count
            $entry["failure_markers"] = [int]$entry["failure_markers"] + [regex]::Matches($tail, '(?i)\b(fail(?:ed|ure)?|timed out)\b').Count
        }
    }

    return @($categories.Values | ForEach-Object { [pscustomobject]$_ })
}

New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null
try {
    $package = Get-Content -LiteralPath (Join-Path $root "package.json") -Raw | ConvertFrom-Json
    $gitStatus = (& git -C $root status --porcelain --untracked-files=no 2>$null | Out-String).Trim()
    $manifest = [ordered]@{
        schema_version = 1
        product = "NIRMIQ Academic Intelligence"
        product_version = [string]$package.version
        created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        operating_system = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
        architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        powershell = $PSVersionTable.PSVersion.ToString()
        python = Get-VersionText "python" @("--version")
        node = Get-VersionText "node" @("--version")
        npm = Get-VersionText "npm.cmd" @("--version")
        git_commit = Get-GitValue @("rev-parse", "--short", "HEAD")
        git_branch = Get-GitValue @("branch", "--show-current")
        tracked_worktree_changes = -not [string]::IsNullOrWhiteSpace($gitStatus)
        local_runtime = [ordered]@{
            api_port_8000_active = Test-LocalPort 8000
            web_port_3002_active = Test-LocalPort 3002
        }
        privacy = [ordered]@{
            raw_logs_included = $false
            environment_variables_included = $false
            database_included = $false
            uploaded_files_included = $false
            document_text_included = $false
            prompts_or_answers_included = $false
            full_local_paths_included = $false
        }
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stagingRoot "manifest.json") -Encoding UTF8

    $doctorScript = Join-Path $PSScriptRoot "release_doctor.ps1"
    $doctorOutput = (& powershell -NoProfile -ExecutionPolicy Bypass -File $doctorScript -Json 2>&1 | Out-String).Trim()
    $doctorExitCode = $LASTEXITCODE
    try {
        $doctor = $doctorOutput | ConvertFrom-Json
        $doctor.workspace = "<local-workspace>"
        $doctor | Add-Member -NotePropertyName exit_code -NotePropertyValue $doctorExitCode -Force
        $doctorJson = $doctor | ConvertTo-Json -Depth 6
    } catch {
        $doctorJson = [ordered]@{
            product = "NIRMIQ Academic Intelligence"
            ready = $false
            exit_code = $doctorExitCode
            detail = "Release Doctor output could not be parsed. Run NIRMIQ Doctor directly for the local-only details."
        } | ConvertTo-Json -Depth 4
    }
    Redact-DiagnosticText $doctorJson | Set-Content -LiteralPath (Join-Path $stagingRoot "doctor.json") -Encoding UTF8

    Get-RuntimeLogSummary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $stagingRoot "runtime-summary.json") -Encoding UTF8
    @"
NIRMIQ safe diagnostics bundle

This archive contains product/runtime versions, Release Doctor results, and aggregate runtime-log counts.
It deliberately excludes raw logs, environment variables, databases, uploaded files, document text,
prompts, answers, source excerpts, filenames, and full local paths.

The archive is created locally and is never uploaded automatically.
"@ | Set-Content -LiteralPath (Join-Path $stagingRoot "README.txt") -Encoding UTF8

    $payload = (Get-ChildItem -LiteralPath $stagingRoot -File | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }) -join "`n"
    foreach ($sensitivePath in @($root, $userHome)) {
        if ($sensitivePath -and $payload.IndexOf($sensitivePath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            throw "Diagnostics privacy verification failed: a local path remained in the generated payload."
        }
    }

    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    Compress-Archive -Path (Join-Path $stagingRoot "*") -DestinationPath $archivePath -CompressionLevel Optimal
} finally {
    if (-not $KeepExpandedFolder -and (Test-Path -LiteralPath $stagingRoot)) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}

if ($OpenFolder) {
    Start-Process -FilePath $outputRoot
}

Write-Output "Safe diagnostics bundle created:"
Write-Output $archivePath
