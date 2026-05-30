# NIRMIQ UI/UX Specification

Last updated: 2026-05-30

Note: the requested filename `UI/UX.md` is represented as `UI_UX.md` because Windows treats `/` as a path separator.

## Design Direction

NIRMIQ should feel like a minimal, technical academic cockpit rather than a generic AI template. The current visual language is dark, calm, precise, and locally intelligent: black glass, cyan/teal evidence accents, compact controls, and strong typography.

## UX Principles

- ChatGPT-like first: ask, upload, read, inspect sources.
- Hide complexity until needed.
- Keep citations available, not constantly overwhelming.
- Make selected source obvious at the point of asking.
- Let the user reclaim reading space by minimizing the composer.
- Avoid exam-only framing; Research and Chat are general document-intelligence lanes.

## Screen Model

### Landing/Login

- Hero headline: NIRMIQ Academic Intelligence.
- Brief value proposition: local grounded academic assistant for papers, notes, textbooks, and question banks.
- Captivating start animation: orbit-style mark animation around the NIRMIQ identity.
- Login fields: name, email, phone.
- Requirement: name plus either email or phone.
- Current auth behavior: local profile gate only, not cloud authentication.

### Main Workspace

- Top nav: Research, Chat, Paper Lab, Exam Lab.
- Right actions: Library and Sources.
- Source cockpit: selected source, chunk count, grounding state, quick summarize/upload/custom PDF actions.
- Conversation thread: primary reading area.
- Composer: compact by default, minimizable.

## Workspace-Specific Composer Behavior

- Research: explains, summarizes, and performs deep document analysis.
- Chat: general local assistant; uses document context if relevant and abstains if not enough context.
- Paper Lab: asks for academic section drafting, related work, limitations, methodology, and citation-backed paragraphs.
- Exam Lab: asks for answer format, marks, question-bank support, study guides, and custom printable PDFs.

## Composer Requirements

- Must include file/photo/document upload.
- Must show the selected source.
- Must support `Minimize` and `Open Search`.
- Must keep the send action visible.
- Must not block response scrolling.
- Must adapt placeholder and action label to the selected workspace.

## Citations UX

- Default: show a compact grounded/citation count on answer cards.
- Evidence chips link to citations.
- Source drawer shows detailed citation cards and source chunks.
- For casual Chat, citations can be hidden unless document context is used.
- For Paper Lab and Exam Lab, citations should be more prominent.

## Accessibility Requirements

- Buttons must have visible focus styles.
- Targets should be comfortably clickable, especially upload and mode controls.
- Sticky composer must not hide focus or response content.
- Text contrast must remain high on dark backgrounds.
- Keyboard navigation should preserve a logical order.

## Known UX Risks

- Too many controls can make NIRMIQ feel like a debug console.
- The source drawer should not be open by default for new users.
- Research answers can become long; the minimized composer is necessary.
- Paper Lab and Exam Lab need stronger guided flows in V4.

## V4 UX Direction

- Guided project setup cards.
- “Explain this document” onboarding flow.
- Citation hover previews.
- Split source reader for long papers.
- Paper Lab templates: literature review, methodology, limitations, abstract.
- Exam Lab templates: 2-mark, 5-mark, 10-mark, study guide, important questions.

