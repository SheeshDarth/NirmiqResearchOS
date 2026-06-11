# NIRMIQ Windows App Packaging

Last updated: 2026-06-11

## Current Recommendation

For the current EOD ship target, NIRMIQ should use a one-click Windows launcher instead of a full installer.

This is worth it now because:

- It gives reviewers a double-click app-like entry point.
- It keeps FastAPI, Next.js, SQLite, Chroma, and local logs easy to debug.
- It avoids rushing a fragile Tauri/PyInstaller bundle.
- It preserves the offline-first architecture.

## One-Click Preview

Double-click from the repository root:

```text
NIRMIQ ResearchOS.cmd
```

This runs:

```powershell
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Stop preview services:

```text
NIRMIQ Stop.cmd
```

## Create Desktop Shortcuts

```powershell
cd C:\Nirmiq-researchOS
.\scripts\create_windows_shortcut.ps1 -Desktop
```

Optional Start Menu shortcuts:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\create_windows_shortcut.ps1 -Desktop -StartMenu
```

## Full Windows Installer Later

A proper Windows installer is possible, but should be a dedicated packaging sprint.

Recommended later path:

1. Build the Next.js app for production.
2. Bundle the FastAPI backend with PyInstaller or a managed Python runtime.
3. Add a Tauri shell that starts the backend as a sidecar.
4. Store SQLite/Chroma data under a user app-data directory.
5. Add installer checks for Ollama and optional local models.
6. Add first-run diagnostics and log export.

Do not do this before the local web/runtime flow is stable and the golden demo path remains green.
