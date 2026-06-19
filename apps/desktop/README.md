# NIRMIQ Desktop Shell

The desktop shell is a lightweight Electron wrapper around the existing local NIRMIQ runtime.

It does not replace the FastAPI backend or Next.js frontend. It starts them locally, opens the app in a desktop window, and gives quick access to logs, docs, project files, and VS Code.

## Why This Exists

- Faster local review than managing browser tabs and terminals.
- One window for upload, analysis, citation review, Paper Lab, and Exam Lab.
- Debug menu for runtime status, logs, project files, and architecture docs.
- Same offline-first behavior as the browser app.

## First Run

From the repository root:

```powershell
npm run desktop:install
```

Then launch:

```powershell
npm run desktop
```

Or double-click:

```text
NIRMIQ Desktop.cmd
```

If you launch an unpacked or portable build from outside the repository and it cannot find the backend/frontend, set:

```powershell
$env:NIRMIQ_ROOT='C:\Nirmiq-researchOS'
```

## Desktop Menu

- `NIRMIQ -> Runtime Status`: check API and web runtime health.
- `NIRMIQ -> Restart Local Runtime`: restart FastAPI and Next.
- `NIRMIQ -> Open In VS Code`: open the repo for immediate edits.
- `NIRMIQ -> Open context.md`: inspect project memory.
- `Logs -> Open API Log`: inspect backend failures.
- `Logs -> Open Web Log`: inspect frontend/runtime failures.

## Packaging

Create an unpacked app folder:

```powershell
npm run desktop:pack
```

Create a portable Windows app:

```powershell
npm run desktop:package
```

Packaging requires desktop dependencies to be installed first. This sprint keeps the shell lightweight instead of bundling Python, Ollama, model files, SQLite, and Chroma into a fragile installer.

The root packaging scripts redirect Electron Builder cache to `temp/electron-builder-cache` so Windows AppData permissions do not block local builds.

The packaged desktop artifact is still a local runtime shell. It expects access to this repository or an explicitly configured `NIRMIQ_ROOT`; it is not yet a fully self-contained installer.
