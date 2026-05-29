import json
from uuid import uuid4

from app.adapters.llm.generator import Generator
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.common import Citation
from app.api.schemas.memory import (
    SessionSummaryResponse,
    SessionTimelineMessage,
    SessionTimelineResponse,
)


class MemoryService:
    def __init__(
        self,
        sqlite_repo: SQLiteRepo,
        generator: Generator,
        model_name: str,
        snapshot_interval_messages: int = 6,
        snapshot_window_messages: int = 12,
    ) -> None:
        self._sqlite_repo = sqlite_repo
        self._generator = generator
        self._model_name = model_name
        self._snapshot_interval_messages = snapshot_interval_messages
        self._snapshot_window_messages = snapshot_window_messages

    async def get_summary(self, session_id: str) -> SessionSummaryResponse:
        summary, count = self._sqlite_repo.get_session_summary(session_id)
        return SessionSummaryResponse(session_id=session_id, summary=summary, message_count=count)

    async def get_timeline(
        self,
        session_id: str,
        limit: int = 24,
    ) -> SessionTimelineResponse:
        summary, count = self._sqlite_repo.get_session_summary(session_id)
        snapshot = self._sqlite_repo.get_latest_memory_snapshot(session_id)
        messages = []
        for row in self._sqlite_repo.get_session_messages(session_id, limit=limit):
            citations = self._decode_citations(row.get("citations_json"))
            retrieval_meta = self._decode_retrieval_meta(row.get("retrieval_meta_json"))
            messages.append(
                SessionTimelineMessage(
                    id=str(row["id"]),
                    role=str(row["role"]),
                    content=str(row["content"]),
                    created_at=row["created_at"],
                    citations=citations,
                    retrieval_meta=retrieval_meta,
                )
            )

        return SessionTimelineResponse(
            session_id=session_id,
            summary=summary,
            message_count=count,
            latest_snapshot_created_at=snapshot["created_at"] if snapshot else None,
            messages=messages,
        )

    async def maybe_refresh_snapshot(self, session_id: str) -> None:
        message_count = self._sqlite_repo.get_session_message_count(session_id)
        if message_count < self._snapshot_interval_messages:
            return
        latest_message = self._sqlite_repo.get_latest_message(session_id)
        if not latest_message:
            return
        latest_snapshot = self._sqlite_repo.get_latest_memory_snapshot(session_id)
        latest_message_id = str(latest_message["id"])
        if latest_snapshot and latest_snapshot.get("window_end_msg_id") == latest_message_id:
            return
        if latest_snapshot and message_count % self._snapshot_interval_messages != 0:
            return

        recent_messages = self._sqlite_repo.get_recent_messages(
            session_id=session_id,
            limit=self._snapshot_window_messages,
        )
        summary = await self._summarize_messages(recent_messages)
        start_id = str(recent_messages[0]["id"]) if recent_messages else None
        end_id = str(recent_messages[-1]["id"]) if recent_messages else None
        self._sqlite_repo.insert_memory_snapshot(
            snapshot_id=str(uuid4()),
            session_id=session_id,
            summary=summary,
            window_start_msg_id=start_id,
            window_end_msg_id=end_id,
        )

    async def _summarize_messages(self, messages: list[dict[str, object]]) -> str:
        if not messages:
            return "No memory summary yet."
        transcript = "\n".join(
            f"{msg['role']}: {str(msg['content'])[:500]}" for msg in messages
        )
        prompt = (
            "Summarize this research conversation memory for future grounding.\n"
            "Return 3-5 concise bullet-like lines in plain text.\n"
            "Focus on user goals, key findings, constraints, and open questions.\n\n"
            f"Conversation:\n{transcript}\n\nSummary:"
        )
        model_summary = await self._generator.answer(prompt=prompt, model=self._model_name)
        if model_summary.strip():
            return model_summary.strip()
        return self._fallback_summary(messages)

    @staticmethod
    def _fallback_summary(messages: list[dict[str, object]]) -> str:
        user_turns = [str(msg["content"]) for msg in messages if msg["role"] == "user"]
        assistant_turns = [str(msg["content"]) for msg in messages if msg["role"] == "assistant"]
        last_user = user_turns[-1] if user_turns else "n/a"
        last_assistant = assistant_turns[-1] if assistant_turns else "n/a"
        lines = [
            f"Conversation turns tracked: {len(messages)}.",
            f"Latest user intent: {last_user[:180]}",
            f"Latest assistant output: {last_assistant[:180]}",
            "Open items: continue retrieval grounding and synthesis refinement.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _decode_citations(raw_value: object) -> list[Citation]:
        if not raw_value:
            return []
        try:
            loaded = json.loads(str(raw_value))
        except json.JSONDecodeError:
            return []
        if not isinstance(loaded, list):
            return []
        citations: list[Citation] = []
        for item in loaded:
            if not isinstance(item, dict):
                continue
            try:
                citations.append(Citation.model_validate(item))
            except Exception:
                continue
        return citations

    @staticmethod
    def _decode_retrieval_meta(raw_value: object) -> dict[str, object] | None:
        if not raw_value:
            return None
        try:
            loaded = json.loads(str(raw_value))
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None
