# Remote Codex Access Plan

Last updated: 2026-05-31

## Goal

Enable Codex to help with NIRMIQ from outside the local desktop while preserving the project's local-first/privacy posture.

## Safe Options

### Option 1: Codex Web With GitHub

Use when:

- The repository is pushed to GitHub.
- You want Codex to open branches or PRs remotely.
- You do not need local private runtime data.

Setup:

1. Rename the GitHub repository to `NirmiqAcademicIntelligenceSystem`.
2. Connect ChatGPT/Codex to the GitHub account.
3. Enable only this repository.
4. Keep `data/`, local PDFs, extracted diagrams, `.env`, SQLite DBs, and Chroma indexes out of Git.
5. Add setup instructions so Codex can install dependencies and run tests.

Privacy posture:

- Source code and committed docs are accessible to cloud Codex.
- Local documents and raw academic files should not be committed.

### Option 2: Codex CLI On The Local Machine

Use when:

- You want Codex working directly in the local workspace.
- You want control over approvals and filesystem access.

Setup:

1. Install Codex CLI.
2. Authenticate with ChatGPT or API key depending on your plan.
3. Run from `C:\Nirmiq-researchOS`.
4. Use Suggest or Auto Edit mode for sensitive work.
5. Avoid Full Auto when private academic documents are present unless the sandbox scope is clear.

Privacy posture:

- Files stay local for reads/writes and commands.
- Prompt/context sent to the model may include relevant snippets or summaries.

### Option 3: Remote Control / Mobile Continuity

Use when:

- You want to monitor or steer ongoing Codex work from mobile or another device.
- Your plan/workspace supports remote control.

Setup depends on current Codex app and workspace access controls.

Privacy posture:

- Your machine remains the host.
- Review prompts, approvals, and command execution carefully.

## NIRMIQ-Specific Rules For Remote Codex

- Do not commit `data/raw`, `data/sqlite`, `data/indexes`, `data/cache`, uploaded PDFs, extracted diagrams, API keys, or `.env`.
- Prefer synthetic/test PDFs for cloud Codex tasks.
- Use GitHub issues/PRs for code changes.
- Keep private academic documents local.
- Use `context.md`, `prd.md`, `trd.md`, `UI_UX.md`, `backend_architecture.md`, `debugging.md`, and this file as Codex onboarding material.

## Recommended Current Path

For now:

1. Keep local desktop Codex as primary.
2. Rename GitHub repo manually to `NirmiqAcademicIntelligenceSystem`.
3. Update `origin` after rename:

```powershell
git remote set-url origin https://github.com/SheeshDarth/NirmiqAcademicIntelligenceSystem.git
git remote -v
```

4. Use Codex Web/GitHub only for code and docs, not private uploaded corpora.

## Local GitHub CLI Status

System MSI install was blocked by a stuck Windows Installer process. A portable GitHub CLI was installed instead:

```powershell
C:\Nirmiq-researchOS\tools\gh\bin\gh.exe --version
```

The portable tool is intentionally ignored by Git via `tools/gh/`.

Authentication still needs to be completed by the user:

```powershell
C:\Nirmiq-researchOS\tools\gh\bin\gh.exe auth login
```

After login, repository rename can be attempted with:

```powershell
C:\Nirmiq-researchOS\tools\gh\bin\gh.exe repo edit SheeshDarth/NirmiqResearchOS --rename NirmiqAcademicIntelligenceSystem
git remote set-url origin https://github.com/SheeshDarth/NirmiqAcademicIntelligenceSystem.git
```
