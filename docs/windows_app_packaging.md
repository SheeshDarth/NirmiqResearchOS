# NIRMIQ Windows App Packaging

Last updated: 2026-06-20

## Current Recommendation

For the current ship target, NIRMIQ should use the new Electron desktop shell instead of a full installer.

This is worth it now because:

- It gives reviewers a double-click desktop entry point.
- It keeps FastAPI, Next.js, SQLite, Chroma, and local logs easy to debug.
- It avoids rushing a fragile Tauri/PyInstaller bundle.
- It preserves the offline-first architecture.
- It gives the developer quick access to VS Code, logs, runtime status, and project docs.

## Desktop App Preview

First install desktop shell dependencies once:

```powershell
cd C:\Nirmiq-researchOS
npm run desktop:install
```

Launch the app:

```powershell
npm run desktop
```

Or double-click from the repository root:

```text
NIRMIQ Desktop.cmd
```

The desktop app starts:

- FastAPI at `http://127.0.0.1:8000`.
- Next.js at `http://127.0.0.1:3002`.
- A NIRMIQ desktop window pointed at the local app.

If an unpacked or portable build is launched from outside the repository and cannot find `apps/api` or `apps/web`, set:

```powershell
$env:NIRMIQ_ROOT='C:\Nirmiq-researchOS'
```

The menu includes:

- Runtime Status.
- Restart Local Runtime.
- Open Project Folder.
- Open In VS Code.
- Open `context.md`.
- Open README.
- Open Debugging Guide.
- Open Backend Architecture.
- Open API/Web logs.

## Browser Preview Fallback

Double-click from the repository root:

```text
NIRMIQ ResearchOS.cmd
```

This runs:

```powershell
.\scripts\run_local.ps1 -OpenBrowser
```

Golden-demo preview is intentionally separate:

```text
NIRMIQ Golden Demo.cmd
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

The shortcut script creates separate entries for normal browser preview, golden-demo preview, desktop app launch, and stop.

## Latest Packaging Validation

Validated on 2026-06-20:

- `npm.cmd run desktop:pack`: passed and generated `dist/desktop/win-unpacked/NIRMIQ ResearchOS.exe`.
- `node --check apps\desktop\src\main.js`: passed.
- `node --check apps\desktop\src\preload.js`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ship_check.ps1`: passed.

Hardening notes:

- Electron now creates its workspace-local `userData` directory before calling `app.setPath`.
- Portable builds also inspect `PORTABLE_EXECUTABLE_DIR` and `PORTABLE_EXECUTABLE_FILE` to find the repository root.
- Desktop-launched child process IDs are mirrored under `temp\runtime` so `scripts\stop_local.ps1` can clean them up reliably.
- Packaging and startup scripts now exit non-zero when npm/native commands fail.

## Full Windows Installer Later

A proper Windows installer is possible, but should remain a dedicated packaging sprint.

Recommended later path:

1. Build the Next.js app for production.
2. Bundle the FastAPI backend with PyInstaller or a managed Python runtime.
3. Bundle the Electron shell and backend launcher.
4. Store SQLite/Chroma data under a user app-data directory.
5. Add installer checks for Ollama and optional local models.
6. Add first-run diagnostics and log export.
7. Add signed releases only after the local runtime and packaging flow are repeatedly green.

Do not do this before the local web/runtime flow is stable and the golden demo path remains green.
