# NIRMIQ UI/UX Specification

Last updated: 2026-06-20

Note: the requested filename `UI/UX.md` is represented as `UI_UX.md` because Windows treats `/` as a path separator.

## Design Direction

NIRMIQ should feel like a minimal, technical academic cockpit rather than a generic AI template. The current visual language is dark, calm, precise, and locally intelligent: black glass, cyan/teal evidence accents, compact controls, and strong typography.

The logo direction is a restrained academic-intelligence mark: geometric, local-first, memory/network inspired, and compatible with the future NIRMIQ ecosystem without making this product look dependent on the rest of the suite.

## Motion Direction

The V3.1 motion layer should communicate intelligence and state, not decoration. Motion is CSS-first and dependency-free to avoid making the local app heavy on CPU/GPU.

Allowed motion:

- Soft page and landing reveal.
- Workspace active-state underline scan.
- Composer minimize/open settle.
- Source drawer slide-in.
- Citation chip stagger.
- Assistant answer reveal.
- One-time grounded/source-ready pulse.

Avoided motion:

- WebGL or canvas effects.
- Particle systems.
- Constantly moving gradients.
- Heavy blur/backdrop filters.
- Loud neon or multi-color animation.
- JavaScript animation loops.

Implementation rules:

- Prefer `transform` and `opacity`.
- Keep timings below roughly 700ms.
- Use `prefers-reduced-motion` to disable motion for users who request it.
- Keep the current graphite, research ivory, oxide copper, deep teal, and sage palette.

## UX Principles

- ChatGPT-like first: ask, upload, read, inspect sources.
- Hide complexity until needed.
- Keep citations available, not constantly overwhelming.
- Make selected source obvious at the point of asking.
- Keep selected-source behavior consistent: if a source is active, normal questions should stay scoped to it unless the user explicitly changes scope.
- Let the user reclaim reading space by minimizing the composer.
- Avoid exam-only framing; Research and Chat are general document-intelligence lanes.
- Golden demo first: reviewers should be able to load a local corpus and run the proof path without understanding backend internals.

## Screen Model

### Landing/Login

- Hero headline: NIRMIQ ResearchOS.
- Brief value proposition: upload, understand, verify, and learn from local academic material.
- Start screen should stay calm and minimal, with no heavy animation or dashboard cards.
- Login fields: name, email, phone.
- Requirement: name plus either email or phone.
- Current auth behavior: local profile gate only, not cloud authentication.

### Main Workspace

- Left sidebar: New Study Thread, recent local threads, Study Material upload, Knowledge Base, runtime status.
- Top nav: compact Research, Chat, Paper Lab, Exam Lab route selector.
- Right action: collapsible Deep Research panel.
- Source cockpit: active sources, chunk count, grounding state, quick summarize/upload/custom PDF actions.
- Conversation thread: primary reading area.
- Composer: compact by default, minimizable.

## Workspace-Specific Composer Behavior

- Research: explains, summarizes, and performs deep document analysis.
- Chat: general local assistant; uses document context if relevant and abstains if not enough context.
- Chat abstentions should read like a useful local-first boundary, not a failure: explain that uploaded context is insufficient and avoid showing citation chips.
- Paper Lab: asks for academic section drafting, related work, limitations, methodology, and citation-backed paragraphs.
- Exam Lab: asks for answer format, marks, question-bank support, study guides, and custom printable PDFs.

## Composer Requirements

- Must include file/photo/document upload.
- Must show active sources.
- Must support `Minimize` and `Open Search`.
- Must keep the send action visible.
- Must not block response scrolling.
- Must adapt placeholder and action label to the selected workspace.
- Minimized composer should become a quiet command pill, not a blank collapsed area.
- Golden demo prompts should be visible but not dominate normal usage.
- Send/Enter should be disabled while a request is busy to prevent duplicate answers.
- Uploads should derive their default title from the selected filename to avoid stale-source confusion.

## Citations UX

- Default: show a compact grounded/citation count on answer cards.
- Evidence chips link to citations.
- Deep Research panel shows detailed citation cards and source chunks.
- For casual Chat, citations can be hidden unless document context is used.
- For Paper Lab and Exam Lab, citations should be more prominent.
- Deep Research can show a compact proof strip with intent, citation coverage, cache state, and source type.
- Error messages should prefer actionable local runtime language over raw API/stack text.
- Success notices should eventually use a separate visual state instead of sharing the error state.

## Accessibility Requirements

- Buttons must have visible focus styles.
- Targets should be comfortably clickable, especially upload and mode controls.
- Sticky composer must not hide focus or response content.
- Text contrast must remain high on dark backgrounds.
- Keyboard navigation should preserve a logical order.

## Known UX Risks

- Too many controls can make NIRMIQ feel like a debug console.
- The Deep Research panel should not be open by default for new users.
- Research answers can become long; the minimized composer is necessary.
- Paper Lab and Exam Lab need stronger guided flows in V4.
- `apps/web/app/page.tsx` still needs a component split before larger visual iteration.
- Mobile scroll and touch-target QA remains required after this hardening pass.

## 2026-06-20 UX Reliability Update

Implemented:

- Active source is attached to submitted queries and exported answer metadata.
- New Study Thread now creates a fresh local session id.
- API requests time out with a local-runtime troubleshooting message.
- Golden-demo preview has a dedicated launcher so normal preview remains clean.

Still to polish:

- Continue the component split into sidebar, chat thread, composer, Deep Research panel, Paper Lab, and Exam Lab. First split completed into `page-model.ts`, `local-login.tsx`, and `study-guide-answer.tsx`.
- Replace shared `setError` success/error state with separate notices.
- Add source preview drawer and stronger mobile QA.

## V4 UX Direction

- Guided project setup cards.
- "Explain this document" onboarding flow.
- Citation hover previews.
- Split source reader for long papers.
- Paper Lab templates: literature review, methodology, limitations, abstract.
- Exam Lab templates: 2-mark, 5-mark, 10-mark, study guide, important questions.
