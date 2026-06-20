from dataclasses import dataclass

from fastapi import Depends, Request

from app.adapters.llm.embedder import Embedder
from app.adapters.llm.generator import Generator
from app.adapters.llm.ollama_client import OllamaClient
from app.adapters.llm.reranker import Reranker
from app.adapters.parsing.pymupdf_parser import PyMuPDFParser
from app.adapters.parsing.tesseract_ocr import TesseractOCR
from app.adapters.retrieval.bm25_index import BM25Index
from app.adapters.storage.chroma_repo import ChromaRepo
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.core.config import Settings, get_settings
from app.domain.retrieval_policy import RetrievalPolicy
from app.services.documents_service import DocumentsService
from app.services.exam_service import ExamService
from app.services.indexing_service import IndexingService
from app.services.ingestion_service import IngestionService
from app.services.memory_service import MemoryService
from app.services.query_service import QueryService
from app.services.retrieval_service import RetrievalService
from app.services.synthesis_service import SynthesisService


@dataclass
class AppContainer:
    sqlite_repo: SQLiteRepo
    chroma_repo: ChromaRepo
    ollama_client: OllamaClient
    generator: Generator
    embedder: Embedder
    reranker: Reranker
    bm25_index: BM25Index
    retrieval_policy: RetrievalPolicy
    parser: PyMuPDFParser
    ocr: TesseractOCR
    indexing_service: IndexingService
    ingestion_service: IngestionService
    documents_service: DocumentsService
    exam_service: ExamService
    memory_service: MemoryService
    retrieval_service: RetrievalService
    synthesis_service: SynthesisService
    query_service: QueryService

    @classmethod
    def from_settings(cls, settings: Settings) -> "AppContainer":
        sqlite_repo = SQLiteRepo(settings.sqlite_path)
        chroma_repo = ChromaRepo(settings.chroma_path)
        ollama_client = OllamaClient(
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
            num_ctx=settings.ollama_num_ctx,
            num_predict=settings.ollama_num_predict,
            num_gpu=settings.ollama_num_gpu,
            num_thread=settings.ollama_num_thread,
        )
        generator = Generator(
            ollama_client=ollama_client,
            default_model=settings.generator_model_default,
            use_ollama=settings.use_ollama_generation,
        )
        embedder = Embedder(
            ollama_client=ollama_client,
            model_name=settings.embed_model,
            use_ollama=settings.use_ollama_embeddings,
            batch_size=settings.ollama_embed_batch_size,
        )
        reranker = Reranker(
            ollama_client=ollama_client,
            model_name=settings.reranker_model,
            use_ollama=settings.use_ollama_reranker,
        )
        bm25_index = BM25Index()
        retrieval_policy = RetrievalPolicy(
            bm25_k=settings.retrieval_k_bm25,
            vector_k=settings.retrieval_k_vector,
            fused_k=settings.retrieval_k_fused,
            rerank_k=settings.retrieval_k_rerank,
            rrf_k=settings.retrieval_rrf_k,
            max_chunks_per_document=settings.retrieval_max_chunks_per_document,
            max_context_tokens=settings.retrieval_max_context_tokens,
            min_grounding_score=settings.retrieval_min_grounding_score,
        )
        parser = PyMuPDFParser(cache_root=settings.parse_cache_path)
        ocr = TesseractOCR()
        indexing_service = IndexingService(
            sqlite_repo=sqlite_repo,
            parser=parser,
            ocr=ocr,
            embedder=embedder,
            chroma_repo=chroma_repo,
        )
        ingestion_service = IngestionService(
            sqlite_repo=sqlite_repo,
            indexing_service=indexing_service,
            upload_root=settings.upload_path,
            allowed_roots=[*settings.local_ingest_allowed_roots, settings.upload_path],
            allow_arbitrary_local_paths=settings.security_allow_arbitrary_local_paths,
            max_upload_bytes=settings.max_request_body_bytes,
        )
        documents_service = DocumentsService(
            sqlite_repo=sqlite_repo,
            chroma_repo=chroma_repo,
            workspace_root=settings.workspace_root,
            parse_cache_path=settings.parse_cache_path,
            upload_root=settings.upload_path,
        )
        exam_service = ExamService(sqlite_repo=sqlite_repo, workspace_root=settings.workspace_root)
        memory_service = MemoryService(
            sqlite_repo=sqlite_repo,
            generator=generator,
            model_name=settings.generator_model_default,
            snapshot_interval_messages=settings.memory_snapshot_interval_messages,
            snapshot_window_messages=settings.memory_snapshot_window_messages,
        )
        retrieval_service = RetrievalService(
            settings=settings,
            policy=retrieval_policy,
            sqlite_repo=sqlite_repo,
            bm25_index=bm25_index,
            reranker=reranker,
            embedder=embedder,
            chroma_repo=chroma_repo,
        )
        synthesis_service = SynthesisService(settings=settings, policy=retrieval_policy, generator=generator)
        query_service = QueryService(
            memory_service=memory_service,
            retrieval_service=retrieval_service,
            synthesis_service=synthesis_service,
            sqlite_repo=sqlite_repo,
        )
        return cls(
            sqlite_repo=sqlite_repo,
            chroma_repo=chroma_repo,
            ollama_client=ollama_client,
            generator=generator,
            embedder=embedder,
            reranker=reranker,
            bm25_index=bm25_index,
            retrieval_policy=retrieval_policy,
            parser=parser,
            ocr=ocr,
            indexing_service=indexing_service,
            ingestion_service=ingestion_service,
            documents_service=documents_service,
            exam_service=exam_service,
            memory_service=memory_service,
            retrieval_service=retrieval_service,
            synthesis_service=synthesis_service,
            query_service=query_service,
        )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_query_service(container: AppContainer = Depends(get_container)) -> QueryService:
    return container.query_service


def get_ingestion_service(
    container: AppContainer = Depends(get_container),
) -> IngestionService:
    return container.ingestion_service


def get_memory_service(container: AppContainer = Depends(get_container)) -> MemoryService:
    return container.memory_service


def get_documents_service(
    container: AppContainer = Depends(get_container),
) -> DocumentsService:
    return container.documents_service


def get_exam_service(container: AppContainer = Depends(get_container)) -> ExamService:
    return container.exam_service
