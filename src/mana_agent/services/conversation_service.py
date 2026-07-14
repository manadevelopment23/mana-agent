"""Persistent dashboard/API conversations integrated with Mana-Agent chat.

Conversations are stored under:
  ~/.mana/repositories/<repository_id>/dashboard/conversations/

Each conversation keeps:
  meta.json          — conversation metadata
  messages.jsonl     — user/assistant/system/tool timeline entries
  events.jsonl       — runtime ChatEvent stream (via ExecutionEventHub)
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from mana_agent.services.execution_event_hub import (
    conversations_root,
    get_execution_event_hub,
    repository_id_for_root,
)
from mana_agent.workspaces.paths import repository_id_for_path
from mana_agent.workspaces.store import atomic_write_json


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


@dataclass
class ConversationMessage:
    message_id: str
    role: str  # user | assistant | system | tool | agent
    content: str
    created_at: str = field(default_factory=_utc_now)
    execution_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationRecord:
    conversation_id: str
    repository_id: str
    root: str
    title: str = "New conversation"
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    status: str = "idle"  # idle | running | failed
    message_count: int = 0
    last_execution_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConversationService:
    """CRUD + message log + chat execution for dashboard/API conversations."""

    def __init__(self, root: str | Path | None = None, *, repository_id: str | None = None) -> None:
        if root is not None:
            self.root = Path(root).expanduser().resolve()
            self.repository_id = repository_id or repository_id_for_path(self.root)
        elif repository_id:
            self.repository_id = repository_id
            self.root = Path(".")
        else:
            raise ValueError("root or repository_id is required")
        self._lock = threading.RLock()
        self._hub = get_execution_event_hub()

    @property
    def base_dir(self) -> Path:
        return conversations_root(self.repository_id)

    def _conversation_dir(self, conversation_id: str) -> Path:
        safe = str(conversation_id or "").strip()
        if not safe.startswith("conv_") or not safe.replace("_", "").isalnum():
            raise ValueError("invalid conversation id")
        return self.base_dir / safe

    def _meta_path(self, conversation_id: str) -> Path:
        return self._conversation_dir(conversation_id) / "meta.json"

    def _messages_path(self, conversation_id: str) -> Path:
        return self._conversation_dir(conversation_id) / "messages.jsonl"

    def create(self, *, title: str = "", metadata: dict[str, Any] | None = None) -> ConversationRecord:
        conversation_id = _new_id("conv")
        record = ConversationRecord(
            conversation_id=conversation_id,
            repository_id=self.repository_id,
            root=str(self.root),
            title=(title or "New conversation").strip() or "New conversation",
            metadata=dict(metadata or {}),
        )
        path = self._meta_path(conversation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, record.to_dict())
        self._messages_path(conversation_id).touch(exist_ok=True)
        return record

    def list(self, *, limit: int = 100) -> list[ConversationRecord]:
        limit = max(1, min(int(limit or 100), 500))
        if not self.base_dir.exists():
            return []
        rows: list[ConversationRecord] = []
        for meta in sorted(self.base_dir.glob("*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(meta.read_text(encoding="utf-8"))
                rows.append(ConversationRecord(**{k: payload.get(k) for k in ConversationRecord.__dataclass_fields__}))
            except Exception:
                continue
            if len(rows) >= limit:
                break
        return rows

    def get(self, conversation_id: str) -> ConversationRecord:
        path = self._meta_path(conversation_id)
        if not path.exists():
            raise FileNotFoundError(conversation_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ConversationRecord(
            conversation_id=str(payload.get("conversation_id") or conversation_id),
            repository_id=str(payload.get("repository_id") or self.repository_id),
            root=str(payload.get("root") or self.root),
            title=str(payload.get("title") or "New conversation"),
            created_at=str(payload.get("created_at") or _utc_now()),
            updated_at=str(payload.get("updated_at") or _utc_now()),
            status=str(payload.get("status") or "idle"),
            message_count=int(payload.get("message_count") or 0),
            last_execution_id=str(payload.get("last_execution_id") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )

    def _save(self, record: ConversationRecord) -> ConversationRecord:
        record.updated_at = _utc_now()
        atomic_write_json(self._meta_path(record.conversation_id), record.to_dict())
        return record

    def get_or_raise(self, conversation_id: str) -> ConversationRecord:
        try:
            return self.get(conversation_id)
        except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise FileNotFoundError(conversation_id) from exc

    def list_messages(self, conversation_id: str, *, limit: int = 500) -> list[ConversationMessage]:
        self.get_or_raise(conversation_id)
        path = self._messages_path(conversation_id)
        if not path.exists():
            return []
        limit = max(1, min(int(limit or 500), 5000))
        lines = path.read_text(encoding="utf-8").splitlines()
        rows: list[ConversationMessage] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                rows.append(
                    ConversationMessage(
                        message_id=str(payload.get("message_id") or _new_id("msg")),
                        role=str(payload.get("role") or "system"),
                        content=str(payload.get("content") or ""),
                        created_at=str(payload.get("created_at") or _utc_now()),
                        execution_id=str(payload.get("execution_id") or ""),
                        metadata=dict(payload.get("metadata") or {}),
                    )
                )
            except Exception:
                continue
        return rows

    def append_message(
        self,
        conversation_id: str,
        *,
        role: str,
        content: str,
        execution_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        record = self.get_or_raise(conversation_id)
        message = ConversationMessage(
            message_id=_new_id("msg"),
            role=str(role or "system").strip().lower(),
            content=str(content or ""),
            execution_id=str(execution_id or ""),
            metadata=dict(metadata or {}),
        )
        path = self._messages_path(conversation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
        record.message_count = int(record.message_count or 0) + 1
        if role == "user" and (record.title in {"", "New conversation"} or record.message_count <= 1):
            record.title = (content.strip().splitlines()[0][:72] if content.strip() else record.title)
        if execution_id:
            record.last_execution_id = execution_id
        self._save(record)
        return message

    def list_events(
        self,
        conversation_id: str,
        *,
        execution_id: str = "",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        self.get_or_raise(conversation_id)
        return self._hub.history(
            conversation_id=conversation_id,
            execution_id=execution_id,
            limit=limit,
            repository_id=self.repository_id,
        )

    def set_status(self, conversation_id: str, status: str, *, execution_id: str = "") -> ConversationRecord:
        record = self.get_or_raise(conversation_id)
        record.status = str(status or "idle")
        if execution_id:
            record.last_execution_id = execution_id
        return self._save(record)

    def get_full(self, conversation_id: str, *, message_limit: int = 500, event_limit: int = 200) -> dict[str, Any]:
        record = self.get_or_raise(conversation_id)
        return {
            "conversation": record.to_dict(),
            "messages": [item.to_dict() for item in self.list_messages(conversation_id, limit=message_limit)],
            "events": self.list_events(conversation_id, limit=event_limit),
        }

    def send_message(
        self,
        conversation_id: str,
        content: str,
        *,
        chat_runner: Callable[..., dict[str, Any]] | None = None,
        emit_events: bool = True,
    ) -> dict[str, Any]:
        """Append a user message, run chat, append assistant reply, emit runtime events.

        ``chat_runner`` defaults to ``run_dashboard_chat``. When provided, it must accept
        ``(prompt, root=..., conversation_id=..., execution_id=..., event_sink=...)``.
        """
        prompt = str(content or "").strip()
        if not prompt:
            raise ValueError("message content is required")
        record = self.get_or_raise(conversation_id)
        execution_id = _new_id("exec")
        self.set_status(conversation_id, "running", execution_id=execution_id)
        user_message = self.append_message(
            conversation_id,
            role="user",
            content=prompt,
            execution_id=execution_id,
        )

        if emit_events:
            self._hub.emit(
                "turn.started",
                title="User message",
                conversation_id=conversation_id,
                execution_id=execution_id,
                repository_id=self.repository_id,
                message=prompt[:240],
                status="running",
                metadata={"role": "user"},
            )
            self._hub.emit(
                "agent.routing",
                title="Routing",
                conversation_id=conversation_id,
                execution_id=execution_id,
                repository_id=self.repository_id,
                message="Model decision routing requested",
                status="running",
            )

        def event_sink(event_type: str, title: str, **kwargs: Any) -> None:
            if not emit_events:
                return
            self._hub.emit(
                event_type,
                title=title,
                conversation_id=conversation_id,
                execution_id=execution_id,
                repository_id=self.repository_id,
                **kwargs,
            )

        runner = chat_runner
        if runner is None:
            from mana_agent.ui.streamlit_helpers import run_dashboard_chat

            def runner(prompt_text: str, **kwargs: Any) -> dict[str, Any]:  # type: ignore[misc]
                return run_dashboard_chat(
                    prompt_text,
                    root=self.root,
                    conversation_id=conversation_id,
                    execution_id=execution_id,
                    event_sink=event_sink,
                )

        try:
            result = runner(prompt, root=self.root, conversation_id=conversation_id, execution_id=execution_id, event_sink=event_sink)
        except TypeError:
            # Older runners without event kwargs.
            result = runner(prompt, root=self.root) if runner is not None else {}
        except Exception as exc:
            self.set_status(conversation_id, "failed", execution_id=execution_id)
            if emit_events:
                self._hub.emit(
                    "error",
                    title="Chat execution failed",
                    conversation_id=conversation_id,
                    execution_id=execution_id,
                    repository_id=self.repository_id,
                    message=str(exc),
                    status="failed",
                )
            raise

        answer = str((result or {}).get("answer") or "")
        assistant = self.append_message(
            conversation_id,
            role="assistant",
            content=answer,
            execution_id=execution_id,
            metadata={
                "mode": (result or {}).get("mode"),
                "sources": (result or {}).get("sources") or [],
            },
        )
        if emit_events:
            self._hub.emit(
                "turn.finished",
                title="Assistant response",
                conversation_id=conversation_id,
                execution_id=execution_id,
                repository_id=self.repository_id,
                message=answer[:240],
                status="success" if answer else "failed",
                metadata={"mode": (result or {}).get("mode")},
            )
        self.set_status(conversation_id, "idle", execution_id=execution_id)
        return {
            "ok": True,
            "conversation_id": conversation_id,
            "execution_id": execution_id,
            "user_message": user_message.to_dict(),
            "assistant_message": assistant.to_dict(),
            "result": result or {},
            "events": self.list_events(conversation_id, execution_id=execution_id, limit=200),
        }


def conversation_service_for_root(root: str | Path) -> ConversationService:
    root_path = Path(root).expanduser().resolve()
    return ConversationService(root=root_path, repository_id=repository_id_for_root(root_path))
