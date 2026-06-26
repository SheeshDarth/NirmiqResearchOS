# Remote Codex Access Plan

Last updated: 2026-06-26

## Goal

Enable Siddharth to steer NIRMIQ work from a phone while preserving the project posture: local-first, private study material stays local, and remote/cloud surfaces are used only when they are the right tool.

## Best Phone Path: Codex App Remote Connections

Use this when you want to control the Codex desktop host from ChatGPT mobile.

What it gives you:

- Start or continue Codex threads from your phone.
- Send follow-up instructions while the Windows host runs the actual workspace.
- Review outputs, diffs, screenshots, and test results.
- Approve actions if your current Codex mode asks for approval.
- Keep the host machine as the place where files, shell commands, plugins, MCP tools, browser tools, and local project context live.

Requirements:

- Latest Codex desktop app running on the Windows host.
- Latest ChatGPT mobile app signed into the same account/workspace.
- The NIRMIQ workspace available on the host machine.
- Host machine awake, online, and not sleeping.
- Workspace/admin settings must allow Remote Control if you are using a managed workspace.

Setup:

1. Open the Codex desktop app on the Windows machine.
2. In the Codex sidebar, choose **Set up Codex mobile**.
3. Scan the QR code with ChatGPT mobile.
4. Finish pairing in ChatGPT mobile.
5. Keep the Windows host awake while you control Codex from the phone.

NIRMIQ-safe usage:

- Use the phone to review work, continue instructions, approve safe edits, and inspect summaries.
- Do not upload private textbooks or local raw data into cloud chats unless you intentionally want that content outside the local machine.
- Keep actual document ingestion and local model testing on the Windows host.
- If Codex asks to expose a server, tunnel, or open a port, pause and verify the privacy impact first.

## Codex Web With GitHub

Use this when:

- You want remote code/documentation work through GitHub.
- You do not need local private runtime data.
- You want branches or PRs created remotely.

Setup:

1. Go to `https://chatgpt.com/codex`.
2. Connect GitHub and authorize only the needed repository.
3. Keep `data/`, uploaded PDFs, `.env`, SQLite DBs, Chroma indexes, parse caches, extracted diagrams, and private notes out of Git.
4. Use `context.md`, `prd.md`, `trd.md`, `UI_UX.md`, `backend_architecture.md`, `debugging.md`, and this file as onboarding material.

Privacy posture:

- Source code and committed docs are available to cloud Codex.
- Local documents and private study material should stay uncommitted.

## Codex CLI Or Desktop On The Local Machine

Use this when:

- You need direct local workspace control.
- You need to run FastAPI, Next.js, Ollama, tests, or the desktop wrapper.
- You need private corpus-aware debugging.

Setup:

1. Open Codex from `C:\Nirmiq-researchOS`.
2. Keep the default local/offline workflow for app testing.
3. Use approvals carefully when private academic documents are present.
4. Prefer synthetic/sample PDFs for public or cloud-shared debugging.

## Advanced Option: SSH Host From Codex App

Use this only if you later run NIRMIQ on another machine.

Safe direction:

- Configure SSH in the Codex App settings under Connections.
- Use SSH config aliases instead of pasting secrets into prompts.
- Make sure the remote host has Codex installed/authenticated and can access the repository.
- Keep private keys out of Git and docs.

## What Not To Do

Avoid exposing Codex App Server WebSocket or NIRMIQ local services directly to the internet.

Reason:

- Experimental app-server transports are for rich clients and local/control-plane scenarios.
- Non-loopback remote listeners can be dangerous if unauthenticated or misconfigured.
- NIRMIQ contains local documents, source paths, generated answers, and SQLite metadata that should not be reachable from the public internet.

Prefer:

- Official Codex mobile remote connection.
- Codex Web with GitHub for source-only tasks.
- SSH forwarding or private VPN only when you understand the security boundary.

## NIRMIQ-Specific Rules For Remote Codex

- Never commit `data/raw`, `data/sqlite`, `data/indexes`, `data/cache`, uploaded PDFs, extracted diagrams, API keys, `.env`, or private notes.
- Keep real textbooks and study material local unless you explicitly choose otherwise.
- Use sample/demo corpora for public screenshots, README demos, and cloud Codex tasks.
- Record major implementation decisions in `context.md` after each phase.
- Push source/docs changes to GitHub, but keep derived local artifacts ignored.

## Current Recommended Workflow

1. Run NIRMIQ locally on Windows for ingestion, retrieval, Ollama, and UI testing.
2. Pair Codex mobile through **Set up Codex mobile** for phone-based steering.
3. Use Codex Web only for code/docs tasks that do not need private local corpora.
4. Keep GitHub branch `v3-foundation` synced until the next major version branch is created.

## Local GitHub CLI Status

System MSI install was blocked by a stuck Windows Installer process earlier. A portable GitHub CLI was installed instead:

```powershell
C:\Nirmiq-researchOS\tools\gh\bin\gh.exe --version
```

The portable tool is intentionally ignored by Git via `tools/gh/`.

Authentication still needs to be completed by the user if repository administration is required:

```powershell
C:\Nirmiq-researchOS\tools\gh\bin\gh.exe auth login
```

After login, repository rename can be attempted with:

```powershell
C:\Nirmiq-researchOS\tools\gh\bin\gh.exe repo edit SheeshDarth/NirmiqResearchOS --rename NirmiqAcademicIntelligenceSystem
git remote set-url origin https://github.com/SheeshDarth/NirmiqAcademicIntelligenceSystem.git
```

## Source Note

This guide was refreshed from the official Codex manual fetched through the `openai-docs` skill on 2026-06-26. Phone remote access is handled by Codex App Remote Connections through ChatGPT mobile, not by exposing NIRMIQ's local FastAPI/Next.js ports to the public internet.
