# UI Guidelines — NIRMIQ ResearchOS

## Theme Name

Academic Intelligence Workspace

## Product Feeling

NIRMIQ should feel like:
- a study command center
- a document intelligence lab
- an academic research workspace
- a trustworthy exam assistant

It should not feel like:
- generic AI SaaS
- neon chatbot
- cyberpunk dashboard
- toy assistant

---

## Core UI Positioning

NIRMIQ is a chatbot.

But not a casual chatbot.

It is a grounded academic assistant.

The UI must make the user feel:

> This answer came from my documents, and I can verify it.

---

## Main Layout

Desktop:

```text
Sidebar       Chat Workspace        Advanced Panel
Documents     Conversation          Evidence Trail
Sessions      Answer                Retrieved Chunks
Modes         Composer              Grounding Data
```

Mobile:
- chat first
- documents in drawer
- advanced panel collapsible

---

## Primary Screens

### 1. Chat Workspace

Purpose:
- ask questions
- receive grounded answers
- prepare for exams

Must show:
- current session
- selected documents
- answer
- citations
- grounding strength

---

### 2. Documents Panel

Purpose:
- upload documents
- inspect index status
- select active materials

Labels:
- Uploaded Material
- Indexed
- Processing
- Failed
- Reindex

---

### 3. Advanced Research Panel

Purpose:
- expose trust and reasoning data

Sections:
- Evidence Trail
- Retrieved Chunks
- Related Concepts
- Grounding Strength
- Confidence
- Documents Used
- Retrieval Profile
- Token Budget

---

### 4. Exam Mode

Purpose:
- make outputs student-useful

Modes:
- Explain Topic
- Answer Question
- Generate Revision Notes
- Important Questions
- Compare Concepts
- Summarize Unit

All modes must remain grounded in documents.

---

## Naming System

Use these product terms:

| Generic Term | NIRMIQ Term |
|---|---|
| Chat | Study Thread |
| Sources | Evidence Trail |
| Confidence | Grounding Strength |
| Files | Study Material |
| Memory | Study Context |
| Debug | Deep Research |
| Documents | Knowledge Base |
| Answer | Grounded Response |

---

## Color Palette

### Background

Deep Graphite

```css
#111418
```

### Surface

Charcoal Slate

```css
#181D23
```

### Elevated Surface

Muted Graphite

```css
#20262E
```

### Primary Text

Research Ivory

```css
#F5F1E8
```

### Secondary Text

Soft Ash

```css
#A7ADB5
```

### Accent

Oxide Copper

```css
#B86A3C
```

### Academic Blue

Deep Teal

```css
#1F4E5F
```

### Memory Accent

Sage Intelligence

```css
#6D8B74
```

### Warning

Amber Marker

```css
#D6A84F
```

### Error

Muted Red

```css
#B85C5C
```

---

## Typography

Headings:
- Space Grotesk

Body:
- Inter

Code:
- JetBrains Mono

Fallback:
- system sans-serif

---

## Components

### Grounded Answer Card

Must include:
- answer
- citations
- grounding strength
- document count
- evidence toggle

---

### Evidence Chip

Example:
`Unit 3 Notes · Page 14`

Use copper accent.

---

### Grounding Meter

Levels:
- Strong
- Moderate
- Weak
- Insufficient

Never use fake precision unless backed by scoring.

---

### Advanced Panel

Should look technical but readable.

Use:
- compact labels
- mono numbers
- collapsible retrieved chunks
- source snippets

---

## Visual Style

Use:
- thin borders
- subtle shadows
- compact spacing
- strong hierarchy
- muted surfaces
- copper highlights

Avoid:
- gradients everywhere
- glowing buttons
- animated particles
- generic AI icons
- robot mascots

---

## Design Tokens

See:
`design/tokens.css`
