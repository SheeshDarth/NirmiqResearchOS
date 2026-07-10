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
