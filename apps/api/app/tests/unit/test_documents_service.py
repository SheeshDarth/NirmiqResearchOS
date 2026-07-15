from pathlib import Path

from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.services.documents_service import DocumentsService


class _UnavailableVectorStore:
    async def clear_all_documents(self) -> bool:
        return False

    async def delete_document(self, document_id: str) -> None:
        return None


def _service(workspace: Path) -> DocumentsService:
    return DocumentsService(
        sqlite_repo=SQLiteRepo(workspace / "data" / "nirmiq.db"),
        chroma_repo=_UnavailableVectorStore(),  # type: ignore[arg-type]
        workspace_root=workspace,
        parse_cache_path=workspace / "data" / "cache",
        upload_root=workspace / "data" / "uploads",
        diagram_root=workspace / "data" / "diagrams",
    )


def test_clear_owned_root_removes_only_files_below_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    owned_root = workspace / "data" / "cache"
    nested_file = owned_root / "nested" / "cache.json"
    top_file = owned_root / "stale.txt"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_text("{}", encoding="utf-8")
    top_file.write_text("stale", encoding="utf-8")
    outside_root = tmp_path / "external"
    outside_file = outside_root / "original.pdf"
    outside_root.mkdir()
    outside_file.write_bytes(b"external")
    service = _service(workspace)

    assert service._clear_owned_root(owned_root) == 2
    assert owned_root.exists()
    assert list(owned_root.iterdir()) == []
    assert service._clear_owned_root(outside_root) == 0
    assert outside_file.exists()


def test_clear_owned_root_rejects_workspace_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    marker = workspace / "do-not-delete.txt"
    workspace.mkdir()
    marker.write_text("keep", encoding="utf-8")
    service = _service(workspace)

    assert service._clear_owned_root(workspace) == 0
    assert marker.exists()
