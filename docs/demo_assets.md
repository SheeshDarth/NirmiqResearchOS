# Demo Assets

NIRMIQ ResearchOS is screenshot-ready, but screenshots should be regenerated after UI changes so the README stays honest.

Recommended GitHub assets:

0. `docs/assets/nirmiq-demo-flow.svg` - committed visual flow diagram for README polish.
1. `docs/assets/01-chat-start.png` - Start state with the golden-demo source selected.
2. `docs/assets/02-grounded-answer.png` - Grounded answer with visible citations and trust state.
3. `docs/assets/03-citation-trail.png` - Source drawer with answer-used passages and hidden full paths.
4. `docs/assets/04-compare-answers.png` - Optional future asset for answer comparison/query diff.
5. `docs/assets/nirmiq-demo.gif` - Optional 20-30 second flow: load demo dataset, ask question, inspect citation.

Suggested capture flow:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Then in the app:

1. Select or load the golden demo source.
2. Ask a locked demo prompt such as `Draft a related work paragraph comparing generic chatbots and document-grounded academic assistants.`
3. Capture the answer with the `Verified` trust cue and citations visible.
4. Open `Sources`.
5. Capture the source drawer with answer-used passages and hidden full paths.

Current note:

- `docs/assets/nirmiq-demo-flow.svg` is committed as a lightweight visual proof path.
- Live UI screenshots for chat start, grounded answer, and citation trail are committed.
- A short GIF and compare-answer screenshot remain optional public-polish assets.
- The README links this checklist so contributors know exactly which assets to capture before publishing.

## Latest Non-Visual Proof

Validated on 2026-07-12:

- `npm.cmd run ship:check`: passed.
- `npm.cmd run desktop:smoke`: passed.
- Golden demo locked prompts returned grounded citations.
- Unsupported demo prompt abstained with no citations.
- The desktop shell verified API/web readiness and `cloud_api_required=false`.

This means screenshots should show a working app, not a planned mockup. If a future UI change lands, rerun the commands above before refreshing screenshots.
