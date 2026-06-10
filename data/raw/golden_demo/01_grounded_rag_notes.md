# Golden Demo Source 01: Grounded Academic Retrieval

NIRMIQ is designed for academic document intelligence, not generic free-form chatting. The central problem it solves is hallucination during study and research. A student may upload lecture notes, textbooks, slides, research papers, lab manuals, or question banks. The assistant should answer from those materials first, cite the evidence it used, and refuse to invent unsupported claims.

Grounded retrieval works as a loop. First, the document is parsed into readable text. Second, the text is split into chunks small enough to retrieve precisely. Third, lexical search and semantic search find candidate chunks. Fourth, Reciprocal Rank Fusion combines search signals so exact keyword matches and meaning-based matches can both help. Fifth, the answer is generated or rewritten using only the retrieved evidence.

The important output is not just an answer. The important output is an answer that can be inspected. Every strong academic answer should include citation anchors such as [1] and source cards that point back to page or chunk evidence. If a sentence makes a claim without evidence, the system should either rewrite it from the source text or mark the answer as needing review.

For students, this reduces anxiety because they can verify where the explanation came from. For early researchers, it improves literature review discipline because claims stay connected to source documents. For engineering project reviewers, it demonstrates real retrieval engineering rather than a thin PDF chatbot.

The golden rule for NIRMIQ is simple: uploaded material remains the source of truth. Memory can help preserve conversation continuity, but memory must not override document evidence. When evidence is weak or unrelated, NIRMIQ should say that it does not have enough grounded context.
