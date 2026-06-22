# Golden Demo Source 02: Offline Runtime And Privacy

NIRMIQ is local-first. Its core workflow should run on the user's machine without requiring a cloud account, payment system, hosted database, or internet connection. The local FastAPI backend handles ingestion, retrieval, synthesis orchestration, memory, and document browsing. The Next.js frontend is a local academic workspace that talks to that backend.

The privacy promise is practical rather than theatrical. Uploaded files are stored under the local data directory. Direct local-path ingestion is restricted to trusted corpus roots, which prevents accidental indexing of private folders. Uploaded file signatures are checked so a renamed file cannot easily masquerade as a PDF or image. A selected document can be removed from the local library, clearing its metadata, chunks, exam records, diagram metadata, and vector entries.

Local inference should degrade gracefully. If Ollama is available, NIRMIQ can use local generation and embeddings. If Ollama is unavailable or too slow, retrieval and fallback synthesis should still produce extractive grounded answers from the indexed documents. This keeps the demo stable on RTX 4050-class hardware and avoids forcing users into cloud APIs.

The low-memory profile is important. NIRMIQ should avoid loading multiple heavy models at once. Generation context, output length, embedding batch size, keep-alive duration, and reranker usage should remain bounded. The system should prefer simple BM25 plus optional vector retrieval over heavy graph databases until measured evidence proves a graph layer is necessary.

The product should make local trust visible. Users should see that their files stay on the machine, that citations can be inspected, and that local material can be removed. A good demo should show one privacy moment: upload material, ask a grounded question, inspect evidence, export useful notes, and remove the source when finished.
