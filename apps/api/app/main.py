from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routers import documents, exam, health, ingest, memory, query
from app.core.config import get_settings
from app.core.deps import AppContainer
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.container = AppContainer.from_settings(settings)
    app.state.container.sqlite_repo.init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="NIRMIQ ResearchOS API",
        version="0.4.0",
        lifespan=lifespan,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.web_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def enforce_request_body_limit(request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        try:
            declared_size = int(content_length) if content_length else 0
        except ValueError:
            declared_size = settings.max_request_body_bytes + 1
        if declared_size > settings.max_request_body_bytes:
            return Response(
                content="Request body too large for local NIRMIQ ingestion limits.",
                status_code=413,
                media_type="text/plain",
            )
        return await call_next(request)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if settings.enable_hsts:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if settings.enable_content_security_policy:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; "
                "img-src 'self' data: blob:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; "
                "connect-src 'self' http://127.0.0.1:8000 http://localhost:8000",
            )
        return response

    routers = (
        (health.router, "/health", ["health"]),
        (ingest.router, "/ingest", ["ingest"]),
        (query.router, "/query", ["query"]),
        (memory.router, "/memory", ["memory"]),
        (documents.router, "/documents", ["documents"]),
        (exam.router, "/exam", ["exam"]),
    )
    for router, prefix, tags in routers:
        app.include_router(router, prefix=prefix, tags=tags)
        app.include_router(router, prefix=f"/api/v1{prefix}", tags=[f"v1:{tag}" for tag in tags])
    return app


app = create_app()
