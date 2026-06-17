"""
mana_analyzer.services.ask_service

Central orchestration layer for answering questions over indexed code context.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable

from mana_analyzer.analysis.models import (
    AskResponse,
    AskResponseWithTrace,
    SearchHit,
    SourceGroup,
)
from mana_analyzer.llm.ask_agent import AskAgent
from mana_analyzer.llm.qna_chain import QnAChain
from mana_analyzer.services.search_service import SearchService
from mana_analyzer.utils.project_search import project_search
from mana_analyzer.vector_store.faiss_store import FaissStore

logger = logging.getLogger(__name__)

SEMANTIC_INDEX_MISSING_WARNING = (
    "Semantic index not found; using direct project search fallback."
)
SEMANTIC_INDEX_HINT = (
    "Semantic index is missing, so I searched the project directly instead. "
    "To enable semantic search later, run: mana-analyzer index"
)


@runtime_checkable
class AskCallback(Protocol):
    def on_event(self, event: str, payload: dict[str, Any] | None = None) -> None:
        ...


class AskService:
    def __init__(
        self,
        store: FaissStore,
        qna_chain: QnAChain,
        ask_agent: AskAgent | None = None,
        search_service: SearchService | None = None,
        project_root: str | Path | None = None,
    ) -> None:
        self.store = store
        self.qna_chain = qna_chain
        self.ask_agent = ask_agent
        self.search_service = search_service
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd().resolve()

    @staticmethod
    def _render_fallback_context(matches: list) -> str:
        blocks: list[str] = []
        for match in matches:
            blocks.append(
                "\n".join(
                    [
                        f"source: {match.file_path}:{match.line_number}",
                        "snippet:",
                        match.line_text,
                    ]
                )
            )
        return "\n\n---\n\n".join(blocks)

    def _project_search_fallback(
        self,
        question: str,
        k: int,
        *,
        root: str | Path | None = None,
    ) -> AskResponse:
        """Answer a question using direct project search when no index is usable.

        Used when the FAISS semantic index is missing or empty, so chat stays
        useful before (or without) running indexing.
        """
        search_root = Path(root).resolve() if root else self.project_root
        result = project_search(question, search_root, max_results=max(5, int(k) * 4))
        warnings = [SEMANTIC_INDEX_MISSING_WARNING]
        if not result.matches:
            return AskResponse(
                answer=(
                    f"{SEMANTIC_INDEX_HINT}\n\n"
                    f"No direct matches for that query under {search_root}."
                ),
                sources=[],
                warnings=warnings,
            )

        sources = [
            SearchHit(
                score=0.0,
                file_path=match.file_path,
                start_line=match.line_number,
                end_line=match.line_number,
                symbol_name="match",
                snippet=match.line_text[:500],
            )
            for match in result.matches
        ]
        context = self._render_fallback_context(result.matches)
        try:
            answer = self.qna_chain.run(question=question, context=context)
        except Exception:
            logger.exception("fallback qna chain failed; returning raw matches")
            answer = (
                f"{SEMANTIC_INDEX_HINT}\n\n"
                + result.format(search_root)
            )
        else:
            answer = f"{SEMANTIC_INDEX_HINT}\n\n{answer}"
        return AskResponse(answer=answer, sources=sources, warnings=warnings)

    @staticmethod
    def _render_context(sources: list[SearchHit]) -> str:
        blocks: list[str] = []
        for src in sources:
            blocks.append(
                "\n".join(
                    [
                        f"source: {src.file_path}:{src.start_line}-{src.end_line}",
                        f"symbol: {src.symbol_name}",
                        "snippet:",
                        src.snippet,
                    ]
                )
            )
        return "\n\n---\n\n".join(blocks)

    # ==========================================================
    # Classic ask
    # ==========================================================

    def ask(self, index_dir: str | Path, question: str, k: int) -> AskResponse:
        resolved_index = Path(index_dir).resolve()
        logger.info("Running ask flow: index_dir=%s k=%d", resolved_index, k)

        try:
            sources = self.store.search(resolved_index, query=question, k=k)
        except Exception:
            logger.warning("Semantic search failed for %s; falling back to project search", resolved_index)
            sources = []

        if not sources:
            logger.info("No indexed context; using direct project search fallback")
            return self._project_search_fallback(question, k)

        context = self._render_context(sources)
        answer = self.qna_chain.run(question=question, context=context)
        return AskResponse(answer=answer, sources=sources)

    # ==========================================================
    # Agent tools (single index)
    # ==========================================================

    def ask_with_tools(
        self,
        index_dir: str | Path,
        question: str,
        k: int,
        max_steps: int = 6,
        timeout_seconds: int = 30,
        callbacks: Sequence[Any] | None = None,
    ) -> AskResponseWithTrace:

        if self.ask_agent is None:
            raise RuntimeError("ask agent is not configured")

        try:
            try:
                return self.ask_agent.run(
                    question=question,
                    index_dir=index_dir,
                    k=k,
                    max_steps=max_steps,
                    timeout_seconds=timeout_seconds,
                    callbacks=callbacks,
                )
            except TypeError:
                return self.ask_agent.run(
                    question=question,
                    index_dir=index_dir,
                    k=k,
                    max_steps=max_steps,
                    timeout_seconds=timeout_seconds,
                )

        except Exception:
            logger.exception("ask agent failed; falling back to classic")

            fallback = self.ask(index_dir=index_dir, question=question, k=k)

            return AskResponseWithTrace(
                answer=fallback.answer,
                sources=fallback.sources,
                mode="classic-fallback",
                trace=[],
                warnings=[],
            )

    # ==========================================================
    # Dir mode
    # ==========================================================

    @staticmethod
    def _group_sources_by_index(
        sources: list[SearchHit],
        index_dirs: list[Path],
    ) -> list[SourceGroup]:

        grouped: dict[Path, list[SearchHit]] = {
            item.resolve(): [] for item in index_dirs
        }

        for source in sources:
            source_path = Path(source.file_path).resolve()
            for index_dir in grouped.keys():
                subproject_root = index_dir.parent.parent if index_dir.parent.name == ".mana" else index_dir.parent
                if subproject_root in source_path.parents:
                    grouped[index_dir].append(source)

        result: list[SourceGroup] = []
        for index_dir, hits in grouped.items():
            if hits:
                result.append(
                    SourceGroup(
                        index_dir=str(index_dir),
                        subproject_root=str(index_dir.parent.parent if index_dir.parent.name == ".mana" else index_dir.parent),
                        sources=hits,
                    )
                )
        return result

    def ask_dir_mode(
        self,
        index_dirs: list[str | Path],
        question: str,
        k: int,
        root_dir: str | Path,
    ) -> AskResponse:

        if self.search_service is None:
            raise RuntimeError("search service is not configured")

        resolved = sorted({Path(p).resolve() for p in index_dirs})

        if not resolved:
            root = Path(root_dir).resolve()
            msg = f"No usable indexes found under {root}"
            return AskResponse(answer=msg, sources=[], warnings=[msg])

        sources, warnings = self.search_service.search_multi(
            index_dirs=resolved,
            query=question,
            k=k,
        )

        if not sources:
            logger.info("No multi-index context; using direct project search fallback")
            fallback = self._project_search_fallback(question, k, root=root_dir)
            fallback.warnings = [*warnings, *fallback.warnings]
            return fallback

        context = self._render_context(sources)
        answer = self.qna_chain.run(question=question, context=context)

        return AskResponse(
            answer=answer,
            sources=sources,
            source_groups=self._group_sources_by_index(sources, resolved),
            warnings=warnings,
        )

    def ask_with_tools_dir_mode(
        self,
        index_dirs: list[str | Path],
        question: str,
        k: int,
        max_steps: int = 6,
        timeout_seconds: int = 30,
        root_dir: str | Path | None = None,
        callbacks: Sequence[Any] | None = None,
    ) -> AskResponseWithTrace:

        if self.ask_agent is None:
            raise RuntimeError("ask agent is not configured")

        resolved = sorted({Path(p).resolve() for p in index_dirs})

        try:
            try:
                result = self.ask_agent.run_multi(
                    question=question,
                    index_dirs=resolved,
                    k=k,
                    max_steps=max_steps,
                    timeout_seconds=timeout_seconds,
                    callbacks=callbacks,
                )
            except TypeError:
                result = self.ask_agent.run_multi(
                    question=question,
                    index_dirs=resolved,
                    k=k,
                    max_steps=max_steps,
                    timeout_seconds=timeout_seconds,
                )
            result.source_groups = self._group_sources_by_index(
                result.sources,
                resolved,
            )
            return result

        except Exception:
            logger.exception("dir-mode agent failed; falling back")

            fallback = self.ask_dir_mode(
                index_dirs=resolved,
                question=question,
                k=k,
                root_dir=root_dir or Path.cwd(),
            )

            return AskResponseWithTrace(
                answer=fallback.answer,
                sources=fallback.sources,
                source_groups=fallback.source_groups or [],
                warnings=fallback.warnings or [],
                mode="classic-dir-fallback",
                trace=[],
            )
