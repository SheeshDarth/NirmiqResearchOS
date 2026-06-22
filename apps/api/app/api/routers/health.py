from fastapi import APIRouter, Depends

from app.core.deps import AppContainer, get_container

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness")
async def readiness_check(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    documents = container.sqlite_repo.list_documents()
    indexed_documents = [document for document in documents if document.get("status") == "indexed"]
    active_chunks = sum(int(document.get("active_chunk_count") or 0) for document in documents)
    ollama_available = await container.ollama_client.is_available()
    vector_available = container.chroma_repo.is_available()
    ready = bool(indexed_documents and active_chunks > 0)
    settings = container.retrieval_service.settings
    return {
        "status": "ready" if ready else "needs_documents",
        "database": "ok",
        "documents": len(documents),
        "indexed_documents": len(indexed_documents),
        "active_chunks": active_chunks,
        "vector_store_available": vector_available,
        "ollama_available": ollama_available,
        "local_first": True,
        "local_backend": True,
        "cloud_api_required": False,
        "external_provider_enabled": False,
        "primary_inference": "local_offline",
        "low_memory_mode": settings.low_memory_mode,
        "ollama_runtime": {
            "keep_alive": settings.ollama_keep_alive,
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": settings.ollama_num_predict,
            "num_gpu": settings.ollama_num_gpu,
            "num_thread": settings.ollama_num_thread,
            "embedding_batch_size": settings.ollama_embed_batch_size,
        },
        "notes": (
            "Ready for grounded document Q&A."
            if ready
            else "Upload or ingest a document before demoing grounded answers."
        ),
    }
