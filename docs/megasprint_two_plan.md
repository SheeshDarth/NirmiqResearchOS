# MegaSprint Two Plan: ChatGPT-Grade Academic UX

Last updated: 2026-07-10

## Sprint Progress

### 2026-07-10 Slice 1: Chat Shell Declutter

Status: implemented and web-build verified.

Changes:

- Compact main header copy and route strip.
- Smaller source/mode pills instead of long helper text.
- Slimmer composer, upload button, send button, and source cockpit.
- Less dashboard-like assistant answer card styling.
- Dense source passage list collapsed by default under `More source passages`.
- Normal UI keeps metadata hidden; Sources remains available on demand.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Remaining:

- Component split.
- Source drawer copy/preview polish.
- First-run/sample-paper path.
- Mobile/laptop visual QA.
- Screenshots/GIF refresh.

### 2026-07-10 Slice 2: First-Run And Source Card Clarity

Status: implemented and web-build verified.

Changes:

- Added a simple first-run sequence: `Upload material -> Ask naturally -> Verify sources`.
- Updated source citation cards to use user-facing `Source` language.
- Added a compact `Used in the answer` reason pill on citations.
- Kept detailed source passages behind collapsed inspection.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

### 2026-07-10 Slice 3: Component Split Start

Status: implemented and web-build verified.

Changes:

- Extracted empty-state onboarding into `apps/web/components/chat-empty-state.tsx`.
- Kept page-level state in `page.tsx` and passed a small suggestion callback into the component.
- Reduced inline JSX in `page.tsx` without touching backend APIs or query behavior.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

### 2026-07-10 Slice 4: Source Evidence Component

Status: implemented and web-build verified.

Changes:

- Extracted the evidence/source inspection UI into `apps/web/components/source-evidence-panel.tsx`.
- Kept page-level retrieval state in `page.tsx`.
- Preserved readable source cards, selected passage preview, and collapsed extra passages.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

### 2026-07-10 Slice 5: Mobile Scroll Guard

Status: implemented and web-build verified.

Changes:

- Small-screen layout now resets inherited desktop `height: 100dvh` behavior.
- Mobile `.study-thread` and `.thread-scroll` use normal page flow so long responses are easier to read.
- Route helper text hides on narrow screens to reduce header crowding.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

## Goal

Make NIRMIQ feel like a simple academic chatbot first, while preserving Research, Chat, Paper Lab, Exam Lab, citations, local privacy, and deep inspection.

MegaSprint One made retrieval much safer. MegaSprint Two should make the product easier to use without exposing retrieval machinery to normal users.

## Product Principle

The user should feel:

```text
Upload material -> ask naturally -> get a clear answer -> open sources only when needed
```

The user should not need to understand:

- BM25.
- Hybrid retrieval.
- Rerank scores.
- Chunk IDs.
- Token counts.
- Internal metadata.
- Debug routing.

## Scope

1. **Chat-first shell**

   Keep the main screen visually close to ChatGPT:

   - Narrow left rail for conversations and active source.
   - Center chat thread as the primary surface.
   - Bottom composer as the main interaction.
   - Sources and Deep Research collapsed by default.

2. **Composer simplification**

   The composer should adapt by mode:

   - Research: attach/upload source, ask, summarize, open sources.
   - Chat: ask general/local questions; abstain if offline and unsupported.
   - Paper Lab: ask for outline, related work, citation synthesis, draft sections.
   - Exam Lab: ask for answer format, marks, study guide, custom PDF export.

3. **Source drawer**

   Replace dense side metadata with a readable drawer:

   - Source title.
   - Page reference.
   - Short excerpt.
   - Why this source was used.
   - Copy citation.

4. **Deep Research as optional inspection**

   Deep Research should stay powerful but hidden:

   - Collapsed by default.
   - Human labels instead of raw metadata.
   - Developer/debug metadata not shown unless a future developer mode is added.

5. **Answer readability**

   Default answers should use:

   - Short answer.
   - Explanation.
   - Key points.
   - Limitations or caveats only when relevant.
   - Paragraph citations where useful.

6. **First-run clarity**

   Add a simple first-run path:

   - Upload a PDF.
   - Or try sample paper.
   - Ask one suggested question.
   - Open one citation.

7. **Responsive QA**

   Verify:

   - Desktop 1920px.
   - Laptop 1366px.
   - Tablet/mobile narrow width.
   - Scroll behavior.
   - Minimized composer behavior.
   - Source drawer behavior.

## Non-Goals

- No new cloud dependency.
- No auth redesign.
- No graph database.
- No multi-agent UI.
- No visible retrieval settings for normal users.
- No new heavy animation library.

## Acceptance Criteria

- Normal chat flow shows no raw retrieval metadata.
- The query/composer area never blocks reading long responses.
- Citations are visible enough to build trust but not noisy.
- Upload is available from the composer.
- Research, Chat, Paper Lab, and Exam Lab remain accessible.
- Mobile/laptop scrolling works.
- `npm.cmd run build` passes.
- Backend tests continue to pass.

## Recommended Implementation Order

1. Split remaining UI shell into smaller components if needed.
2. Reduce visible header/chip clutter.
3. Convert Deep Research to a source drawer with collapsed detail sections.
4. Improve answer typography and spacing.
5. Add first-run/sample-paper guidance.
6. Run manual UI QA across common widths.
7. Update screenshots/GIFs and README.

## Progress Log

### 2026-07-11 Slice 6: Thread Header Component

Status:

- Completed and build-verified.

Implemented:

- Extracted the chat thread header into `apps/web/components/thread-header.tsx`.
- Kept the same Library and Sources toggles, active-source pill, workspace chip, and route hint.
- Reduced `apps/web/app/page.tsx` to `1645` lines.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- MegaSprint Two needs a cleaner component boundary before bigger UX edits.
- Isolating the header reduces the chance of accidental query, retrieval, or feedback regressions while iterating on the visual shell.

### 2026-07-11 Slice 7: Chat Thread Component

Status:

- Completed and build-verified.

Implemented:

- Extracted the answer/thread renderer into `apps/web/components/chat-thread.tsx`.
- Preserved user bubbles, assistant answers, trust badges, source drawer chips, citation jump behavior, and feedback buttons.
- Reduced `apps/web/app/page.tsx` to `1569` lines.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- The main page now owns orchestration instead of also owning the detailed answer renderer.
- This makes later answer readability and source-drawer polish safer because the chat-turn surface has its own component boundary.

### 2026-07-11 Slice 8: Composer Component

Status:

- Completed and build-verified.

Implemented:

- Extracted the bottom composer into `apps/web/components/chat-composer.tsx`.
- Preserved upload, active-source display, ask/send, minimized state, workspace tools, summarize/export/source actions, and advanced route/retrieval controls.
- Reduced `apps/web/app/page.tsx` to `1415` lines.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- The composer is the most sensitive UI surface because it owns upload, query submission, and mode routing.
- Separating it creates a safer boundary for future upload-flow and mobile-composer polish without moving backend or retrieval behavior.

### 2026-07-11 Slice 9: Readable Answer Source Drawer

Status:

- Completed and build-verified.

Implemented:

- Replaced tiny answer citation chips with compact source preview cards inside `ChatThread`.
- Showed source number, page/page range, and a short citation excerpt while keeping raw metadata hidden.
- Kept the cards collapsed by default and wired to the existing Sources panel jump behavior.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- Users can now verify why an answer is grounded without decoding small citation chips.
- This improves trust and readability while preserving the simple chat-first interface.

### 2026-07-11 Slice 10: Responsive Source Polish

Status:

- Completed and build-verified.

Implemented:

- Hardened source preview cards against narrow-width overflow.
- Stacked source preview metadata on mobile so page labels do not squeeze excerpts.
- Improved wrapped quick-action touch height for composer/source controls.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- The new readable source drawer needs to work on laptop and mobile widths, not just desktop.
- This keeps the chat flow usable while preserving the hidden-metadata design rule.

### 2026-07-11 Slice 11: Answer Readability Polish

Status:

- Completed and build-verified.

Implemented:

- Tightened answer line length and improved structured answer spacing.
- Added clearer first-paragraph, heading, and bullet styling.
- Added mobile-specific answer font sizing and wrapping guards.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- Better retrieval still needs readable presentation; dense answer text can make correct answers feel worse than they are.
- This keeps the normal chat flow calmer and easier to scan without exposing metadata.

### 2026-07-11 Slice 12: Interaction Comfort Polish

Status:

- Completed and build-verified.

Implemented:

- Increased answer feedback button hit areas.
- Increased compact source/composer quick-action hit areas.
- Improved the clear-thread control tap surface without exposing extra UI.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- A ChatGPT-grade UI is not only simpler visually; it must also be easy to operate repeatedly.
- This reduces fiddly interactions while preserving the minimized metadata and chat-first layout.

### 2026-07-11 Slice 13: Tap Feedback Polish

Status:

- Completed and build-verified.

Implemented:

- Added `touch-action: manipulation` for core interactive elements.
- Added subtle pressed-state feedback to chat, source, composer, feedback, and workspace controls.
- Kept the visual footprint unchanged and avoided adding new controls or metadata.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- The simplified UI should feel reliable when clicked or tapped repeatedly.
- Immediate press feedback helps the app feel more native without increasing complexity.

### 2026-07-11 Slice 14: Generation Status Polish

Status:

- Completed and build-verified.

Implemented:

- Added a temporary assistant pending bubble during query generation.
- Added polite live-region semantics for the query-running state.
- Kept the pending state concise and source-focused: `Reading your selected material and checking the sources...`.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- Users should not wonder whether the app froze after pressing Ask.
- A small in-thread pending state makes NIRMIQ feel closer to a familiar chatbot while preserving the academic grounding model.

### 2026-07-11 Slice 15: Composer Status Clarity

Status:

- Completed and build-verified.

Implemented:

- Added live composer status labels for upload, query, demo loading, and normal source selection.
- Added polite live-region semantics to the composer source status.
- Added a subtle working source dot for active local operations.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- Uploading and indexing can take time locally, and users need to know the app is working.
- This improves first-run confidence while keeping the ChatGPT-like composer compact.

### 2026-07-11 Slice 16: Safe-Area Responsive Polish

Status:

- Completed and build-verified.

Implemented:

- Added safe-area-aware padding to the chat thread and composer.
- Protected the compact bottom composer from OS/browser chrome crowding.
- Kept layout, controls, metadata visibility, and backend behavior unchanged.

Verification:

- `npm.cmd run build` from `apps/web`: passed.

Why this matters:

- ChatGPT-grade UI needs to feel stable in phone-width previews and desktop app wrappers.
- This reduces the chance that the ask box or response area feels cramped near system edges.
