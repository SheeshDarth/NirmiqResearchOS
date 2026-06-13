# Demo Assets

NIRMIQ ResearchOS is screenshot-ready, but screenshots should be regenerated after UI changes so the README stays honest.

Recommended GitHub assets:

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

- Actual screenshots are not committed in this pass because no local screenshot-capable browser tool was available in the current Codex session.
- The README links this checklist so contributors know exactly which assets to capture before publishing.
