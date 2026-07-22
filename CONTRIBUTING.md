# Contributing To NIRMIQ Academic Intelligence

Thanks for taking a look at NIRMIQ. This repo is intentionally optimized for a
solo-developer, local-first academic document intelligence workflow.

## Project Principles

- Local-first by default.
- No cloud/API dependency for the core app.
- Retrieval quality before larger models.
- Simple UI before more controls.
- Evidence-backed answers before fluent guesses.
- Maintainable code before clever abstractions.

## Local Setup

```powershell
git clone https://github.com/SheeshDarth/NirmiqResearchOS.git
cd NirmiqResearchOS
.\scripts\bootstrap.ps1
npm.cmd run start:golden
```

Open `http://127.0.0.1:3002`.

## Useful Commands

```powershell
npm.cmd run doctor
npm.cmd run test:api
npm.cmd run compile:api
npm.cmd run build
npm.cmd run ship:check
npm.cmd run qa:real-user
```

Use `npm.cmd run qa:real-user` only for local feedback review. Generated files under
`temp/real_user_qa` are private local artifacts and should not be committed.

## Contribution Checklist

- Keep public API request shapes stable unless the change is explicitly versioned.
- Preserve offline operation without Ollama, Chroma, reranker, or cloud services.
- Hide raw retrieval metadata from the normal user interface.
- Add or update tests for retrieval, citation, privacy, or startup behavior when touched.
- Update `context.md` and relevant docs when behavior changes.
- Do not commit local databases, uploads, extracted diagrams, logs, temp files, or private PDFs.

## Pull Request Expectations

- Explain what changed and why.
- Include verification commands and results.
- Mention any tradeoffs or known limits.
- Keep unrelated changes out of the PR.
- Use the PR template.

## Accuracy Changes

Retrieval and synthesis changes should be measured rather than tuned by vibes.

Preferred evidence:

- `npm.cmd run eval:answer-quality`
- `npm.cmd run eval:hard-docs`
- `npm.cmd run eval:summary-reliability`
- Promoted real-user QA labels with expected evidence phrases.

Do not increase model size, temperature, context length, or cloud dependency as the
first fix for bad answers. Improve evidence selection and answer grounding first.
