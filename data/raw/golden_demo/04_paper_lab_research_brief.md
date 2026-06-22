# Golden Demo Source 04: Paper Lab Research Brief

A useful academic intelligence system can support early paper drafting without pretending to replace research judgment. Paper Lab should help the user transform a document corpus into structured sections such as thesis framing, related work, method summary, limitations, and future work. It should not invent papers or citations that were not present in the uploaded material.

The research claim for this demo is: local-first retrieval systems can make academic AI more trustworthy by combining offline operation, source-grounded synthesis, citation inspection, and abstention. This claim should be supported by evidence from the corpus: grounded retrieval reduces unsupported claims, local runtime protects student documents, and exam workflows show that source-backed answers can be formatted for learning.

A related-work paragraph should compare generic chatbots with document-grounded academic assistants. Generic chatbots are useful for brainstorming, but they may lose document context, provide uncited explanations, or answer from broad model memory. Document-grounded assistants are narrower but more auditable: they retrieve local chunks, cite evidence, expose source snippets, and can refuse unrelated questions.

A methods paragraph for NIRMIQ should mention FastAPI orchestration, SQLite session and document storage, BM25 and optional vector retrieval, Reciprocal Rank Fusion, local Ollama generation when available, and deterministic fallback synthesis when local generation is unavailable. The method is intentionally lightweight so a solo developer can maintain it.

Limitations should be honest. Retrieval quality depends on document parsing, chunk quality, and whether the user uploaded enough relevant material. OCR quality can affect scanned PDFs and images. A small local model may write less fluently than a cloud frontier model, so the system should prioritize grounded correctness over style. These limitations are acceptable for an MVP because the product's trust value comes from evidence visibility.
