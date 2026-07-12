# NIRMIQ UI/UX Specification

Last updated: 2026-07-10

Note: the requested filename `UI/UX.md` is represented as `UI_UX.md` because Windows treats `/` as a path separator.

## Design Direction

NIRMIQ should feel like a minimal academic chatbot, not a dashboard cockpit. The current visual language stays dark, calm, precise, and locally intelligent, but the interaction priority is now: ask naturally, read clearly, verify only when needed.

The logo direction is a restrained academic-intelligence mark: geometric, local-first, memory/network inspired, and compatible with the future NIRMIQ ecosystem without making this product look dependent on the rest of the suite.

## MegaSprint One UX Rule

Normal users should see:

- A simple answer.
- Citations only where useful.
- One compact trust state: `Verified`, `Needs more evidence`, or `Not found in sources`.
- A Sources panel with readable passages and page references.

Normal users should not see:

- Scores.
- Chunk ids.
- Token counts.
- Local file paths.
- Reliability-gate reason codes.
- Retrieval metadata unless a future developer mode is explicitly enabled.

## MegaSprint Two UX Rule

The main workspace should now behave like a focused academic chatbot:

- Header stays compact and does not compete with the answer.
- Composer is the primary control surface.
- Upload, Library, Sources, and Tools are available but secondary.
- Dense source passage lists stay collapsed by default.
- Assistant answers use a calmer reading surface rather than a heavy dashboard card.
- Route/mode information appears as small context pills, not a dashboard control strip.
- The normal user should never need to understand retrieval mode, profile, chunk count, or ranking metadata to ask a good question.

Slice 1 implementation:

- Main header copy simplified to `Ask NIRMIQ`.
- Long helper copy in the route strip replaced with compact source/mode state.
- Composer spacing reduced so answers get more room.
- Minimized composer copy simplified to `Composer minimized` and `Ask next`.
- Source drawer now hides extra passages behind `More source passages`.
- Web build passed after the update.

Slice 2 implementation:

- First-run empty state now explains the core loop in three steps: upload, ask, verify.
- Citation cards now use `Source` language and page references instead of feeling like internal chunks.
- Each citation card includes a quiet `Used in the answer` reason pill.
- Web build passed after the update.

Slice 3 implementation:

- Empty-state onboarding moved into `apps/web/components/chat-empty-state.tsx`.
- Main `page.tsx` keeps state orchestration, while the onboarding component owns first-run presentation.
- Web build passed after the extraction.

Slice 4 implementation:

- Source inspection moved into `apps/web/components/source-evidence-panel.tsx`.
- The source panel remains readable and user-facing: source title, page, usage reason, excerpt, selected passage, and collapsed extra passages.
- Web build passed after the extraction.

Slice 5 implementation:

- Small-screen layout now avoids inheriting desktop `100dvh`/hidden-overflow constraints.
- Thread content can use normal page flow on mobile so long answers and the composer do not trap scrolling.
- Route helper copy hides on narrow screens to reduce visual pressure.
- Web build passed after the responsive guard.

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
- Treat Research, Paper, Exam, and Chat as quiet tool hints near the composer, not as dashboard tabs that make users choose the correct system mode.
- The default visible route is Auto: the user asks naturally and backend intent routing decides summary, factual lookup, comparison, paper draft, exam-style answer, or abstention.
- Keep evaluation/debug surfaces out of the normal product shell. Retrieval evaluation belongs in scripts, docs, and developer workflows.
- Do not show full local filesystem paths, chunk hashes, raw retrieval scores, cache state, or intent routing in normal user-facing UI.
- Use plain labels: Sources, Check the answer, Analyze a paper, Study for exam, Research deeply.
- Make selected source obvious at the point of asking.
- Keep selected-source behavior consistent: if a source is active, normal questions should stay scoped to it unless the user explicitly changes scope.
- Let the user reclaim reading space by minimizing the composer.
- Avoid exam-only framing; Research and Chat are general document-intelligence lanes.
- Golden demo first: reviewers should be able to load a local corpus and run the proof path without understanding backend internals.
- Answer feedback should be quiet and answer-level: `Good` and `Needs work`, not a ratings dashboard.

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
- Assistant answer footer: compact trust line, optional sources drawer, and quiet local feedback controls.
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
- Tool chips should stay compact: `Auto`, `Chat`, `Paper`, `Exam`.
- Normal questions should not inherit stale one-click modes like Summary. Summary remains an explicit action or backend-detected intent.

## Answer Presentation Contract

- Default answer shape: `Direct answer`, `Key points`, `Evidence note`.
- List and algorithm questions should produce concise lists, not pasted textbook paragraphs.
- Citations should appear in answer text and compact source chips, with detailed chunks only in Sources.
- Abstention should be clear and useful: say what context is missing instead of pretending support exists.
- The answer column should stay readable around 65-70 characters per line.
- Feedback controls should stay visually lighter than the answer and citations so they help testing without making the product feel crowded.

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

## 2026-07-08 Minimal Chatbot Interface Pass

Goal:

- Make NIRMIQ feel closer to ChatGPT: one clear conversation surface, one composer, one obvious upload path, and optional tools hidden until needed.

Implemented:

- The default composer now shows only the essential flow: attached source, upload, library, text input, and ask.
- Workspace modes, summarize, export, sources, minimize, new thread, and advanced retrieval settings now live behind a compact `Tools` disclosure.
- The minimized composer now has an explicit `Ask` affordance so users can reopen it without guessing.
- The active source language changed to an attachment mental model, which is easier for non-technical users.
- Composer styling is lower-profile: narrower width, shorter textarea, calmer border treatment, and less visible metadata.

Design rule going forward:

- If a control is not needed for the next user message, it should not be permanently visible.
- Trust cues should stay visible on answers, while evidence details belong in Sources or Deep Research.
- Paper Lab and Exam Lab should remain available, but not compete with the primary chat flow.

Remaining debt:

- Split `apps/web/app/page.tsx` into focused components before the next major visual iteration.
- Perform mobile visual QA and keyboard navigation QA.
- Replace the current disclosure-based power tools with a cleaner drawer once the component split lands.

## 2026-07-11 MegaSprint Two Header Component Split

Goal:

- Keep moving the interface toward a simpler ChatGPT-grade shell by separating UI structure from query orchestration.

Implemented:

- Added `ThreadHeader` as a focused component for brand, page title, Library toggle, Sources toggle, selected-source status, and compact route hint.
- Preserved existing interaction copy and behavior so this remains a safe maintainability improvement.
- Reduced the main page file size, making later UI simplification less risky.

UX rationale:

- The chat header is a stable visual boundary and should not live inside the same block as query history, feedback, composer, and retrieval state.
- Smaller UI components make it easier to remove clutter without accidentally breaking upload, query, or citation behavior.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Answer Readability Polish

Goal:

- Make source-grounded answers feel easier to read and less dense without changing backend behavior.

Implemented:

- Reduced answer line measure and refined paragraph rhythm.
- Added stronger first-paragraph emphasis and clearer heading hierarchy.
- Improved bullet indentation and mobile answer sizing.

UX rationale:

- NIRMIQ's answers should feel like a clear academic assistant, not a block of extracted text.
- Presentation cannot fix weak retrieval, but it can make good evidence-backed answers much easier to trust and scan.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Responsive Source Polish

Goal:

- Make the readable source drawer and composer action rows safer on mobile and laptop widths.

Implemented:

- Added overflow guards for source preview cards and excerpts.
- Stacked source preview metadata on narrow screens.
- Increased wrapped quick-action touch height in mobile layouts.

UX rationale:

- Source previews are only useful if they stay readable when the user resizes the desktop app or tests on a phone-width viewport.
- This keeps verification lightweight and readable without exposing raw retrieval metadata.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Source Drawer Readability

Goal:

- Let users inspect answer sources from the chat flow without making the default answer view feel technical.

Implemented:

- Replaced the compact citation-only drawer chips with source preview cards.
- Each card shows source number, page/page range, and a short source excerpt.
- Kept the drawer collapsed by default and retained the deeper Sources panel for exact passage inspection.

UX rationale:

- Trust cues are stronger when users can see a short source excerpt without leaving the answer.
- The UI remains simple because detailed sources are still hidden until the user opens the drawer.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Composer Component Split

Goal:

- Separate the bottom ask/upload composer from the page shell while keeping the product flow unchanged.

Implemented:

- Added `ChatComposer` for active material display, upload, textarea, ask button, minimized composer state, tools disclosure, workspace chips, and advanced settings.
- Kept query execution, upload ingestion, workspace routing, source opening, and retrieval state owned by the page.
- Reduced the main page file again, making future composer UX polish less risky.

UX rationale:

- The composer is the user's main control surface, so future improvements need a focused component boundary.
- This split prepares for cleaner upload state, mobile sizing, and reduced visible control density without mixing those changes into RAG logic.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Chat Thread Component Split

Goal:

- Move answer rendering out of the page shell so the main UI becomes easier to simplify without breaking feedback or citations.

Implemented:

- Added `ChatThread` as a focused component for user bubbles, assistant answers, trust badges, source drawer chips, and answer feedback.
- Kept `Open Sources` and citation jump behavior delegated back to the page so source inspection state remains centralized.
- Reduced the main page file further, preparing for safer composer and source-drawer polish.

UX rationale:

- The answer area is the product's primary surface and deserves its own boundary.
- Keeping the answer renderer isolated makes future readability improvements easier to review, test, and undo if needed.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Interaction Comfort Polish

Goal:

- Make the compact chat shell easier to use on laptop and touch-width layouts without increasing visual complexity.

Implemented:

- Increased secondary action hit areas for feedback, source/composer quick actions, and clear-thread.
- Kept controls visually compact and aligned with the current minimal NIRMIQ theme.
- Preserved hidden metadata and the existing composer/source workflows.

UX rationale:

- Small controls make a simplified interface feel fragile even when the information architecture is correct.
- Comfortable hit areas make the app feel calmer, more intentional, and more demo-ready.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Tap Feedback Polish

Goal:

- Improve perceived responsiveness without adding heavier animation or visual noise.

Implemented:

- Added `touch-action: manipulation` to primary interactive primitives.
- Added subtle pressed-state transforms to buttons, source preview cards, workspace chips, feedback pills, and clear-link controls.
- Kept reduced-motion support intact through the existing global reduced-motion rule.

UX rationale:

- ChatGPT-style interfaces feel calm partly because interactions respond immediately and predictably.
- This strengthens the product feel while preserving NIRMIQ's minimal academic theme.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Generation Status Polish

Goal:

- Improve perceived reliability while a local query is running.

Implemented:

- Added a temporary assistant pending bubble when NIRMIQ is generating an answer.
- Added `aria-live="polite"` to announce the status without being disruptive.
- Styled the state as a subtle assistant message rather than a dashboard notification.

UX rationale:

- Local-first RAG can take a moment, especially on lower-end devices, so the answer area needs visible progress.
- Keeping the status inside the thread preserves the ChatGPT-like mental model: ask, wait in the conversation, receive answer.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Composer Status Clarity

Goal:

- Make local upload/query state obvious from the composer itself.

Implemented:

- Composer now shows `Uploading`, `Reading`, `Loading`, or `Using` based on existing busy state.
- Status text explains the current action in plain language without file paths, scores, or debug metadata.
- Added a subtle working dot and polite live-region semantics.

UX rationale:

- A local-first app can feel broken if indexing or generation takes a few seconds with no clear status.
- The composer is the user's main control surface, so it should calmly explain what is happening.

Verification:

- `npm.cmd run build`: passed.

## 2026-07-11 MegaSprint Two Safe-Area Responsive Polish

Goal:

- Improve responsive comfort without altering the simplified chat interface.

Implemented:

- Added safe-area-aware side gutters to the chat scroll region.
- Added safe-area-aware side and bottom padding to the composer wrapper.
- Preserved the compact/minimized composer behavior.

UX rationale:

- The composer is the primary action surface, so it must not collide with browser/app chrome or mobile safe areas.
- This keeps the app feeling calm and native while staying visually minimal.

Verification:

- `npm.cmd run build`: passed.
# MegaSprint Two Recovery - 2026-07-12

The previous MegaSprint Two implementation improved component boundaries but failed visual acceptance because the same dashboard-like information architecture remained visible.

The active interface direction is now:

- One chat canvas is the product home.
- Navigation and the document library live in an overlay left drawer.
- Sources, Paper Lab tools, and Exam Lab tools live in an overlay right drawer.
- Research, Chat, Paper Lab, and Exam Lab use one compact composer mode selector.
- Upload remains directly accessible from the composer.
- Answers render as readable assistant content, not bordered dashboard cards.
- Normal answers show only a compact trust state, source count when available, and copy action.
- Dates, chunk counts, paths, retrieval methods, model metadata, and reviewer controls stay out of the normal chat flow.
- Golden Demo and destructive local-data controls remain available under advanced local tools.
- The composer stays available after an answer and is never minimized automatically.

Visual language:

- Near-black neutral surfaces with restrained copper and sage accents.
- Typography and whitespace establish hierarchy; color is not used as decoration.
- Motion is limited to drawer transitions, loading state, and answer arrival.
- Drawers overlay the chat instead of reducing the response width.
- Desktop and mobile both preserve one primary vertical scroll region.

Acceptance requires a user-visible review, not only `npm run build`.

Current recovery verification:

- Desktop main shell inspected visually at 1426x922.
- Navigation/library drawer overlays the conversation and has an independent material list scroll.
- Source drawer overlays the right side and keeps the answer canvas intact.
- Header and composer remain fixed while the central response region owns vertical scrolling.
- Production bundle remains approximately `117 kB` first-load JavaScript.
