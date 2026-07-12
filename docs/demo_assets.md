# Demo Assets

NIRMIQ ResearchOS is screenshot-ready, but screenshots should be regenerated after UI changes so the README stays honest.

Recommended GitHub assets:

0. `docs/assets/nirmiq-demo-flow.svg` - committed visual flow diagram for README polish.
1. `docs/assets/01-upload-pdf.png` - Upload or load the sample PDF.
2. `docs/assets/02-ask-grounded-question.png` - Ask a document-grounded question.
3. `docs/assets/03-citation-trail.png` - Open Deep Research and show source chunks/citations.
4. `docs/assets/04-compare-answers.png` - Show answer comparison or query diff.
5. `docs/assets/nirmiq-demo.gif` - 20-30 second flow: load demo dataset, ask question, inspect citation.

Suggested capture flow:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\start_local.ps1 -OpenBrowser
.\scripts\load_demo_dataset.ps1
```

Then in the app:

1. Select `NIRMIQ Demo - RAG Reference Notes`.
2. Ask: `How does NIRMIQ reduce hallucinations?`
3. Open the Deep Research panel.
4. Click an evidence chip.
5. Capture the answer and citation trail.

Current note:

- `docs/assets/nirmiq-demo-flow.svg` is committed as a lightweight visual proof path.
- Actual UI screenshots/GIFs still need to be captured from a live browser after final visual QA.
- The README links this checklist so contributors know exactly which assets to capture before publishing.

## Latest Non-Visual Proof

Validated on 2026-07-12:

- `npm.cmd run ship:check`: passed.
- `npm.cmd run desktop:smoke`: passed.
- Golden demo locked prompts returned grounded citations.
- Unsupported demo prompt abstained with no citations.
- The desktop shell verified API/web readiness and `cloud_api_required=false`.

This means screenshots should show a working app, not a planned mockup. If a future UI change lands, rerun the commands above before refreshing screenshots.
