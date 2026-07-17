from __future__ import annotations

import logging

from mana_agent.analysis.models import CodeChunk, CodeSymbol

logger = logging.getLogger(__name__)


class CodeChunker:
    def __init__(self, max_chars: int = 1800, overlap: int = 200) -> None:
        self.max_chars = max_chars
        self.overlap = overlap

    def _chunk_text(self, text: str) -> list[str]:
        return [chunk for chunk, _, _ in self._chunk_text_with_offsets(text)]

    def _chunk_text_with_offsets(self, text: str) -> list[tuple[str, int, int]]:
        if len(text) <= self.max_chars:
            return [(text, 0, len(text))]

        chunks: list[tuple[str, int, int]] = []
        step = max(self.max_chars - self.overlap, 1)
        start = 0
        while start < len(text):
            end = min(start + self.max_chars, len(text))
            chunks.append((text[start:end], start, end))
            if end >= len(text):
                break
            start += step
        return chunks

    @staticmethod
    def _source_line_range(
        symbol: CodeSymbol,
        *,
        source_offset: int,
        chunk_start: int,
        chunk_end: int,
    ) -> tuple[int, int]:
        source_start = max(chunk_start - source_offset, 0)
        source_end = min(max(chunk_end - source_offset, 0), len(symbol.source))
        if source_start >= source_end:
            return symbol.start_line, symbol.start_line

        start_line = symbol.start_line + symbol.source[:source_start].count("\n")
        end_line = symbol.start_line + symbol.source[:source_end].count("\n")
        if source_end > 0 and symbol.source[source_end - 1] == "\n":
            end_line -= 1
        return (
            min(max(start_line, symbol.start_line), symbol.end_line),
            min(max(end_line, start_line), symbol.end_line),
        )

    def build_chunks(self, symbols: list[CodeSymbol]) -> list[CodeChunk]:
        logger.debug("Building chunks for %d symbols", len(symbols))
        output: list[CodeChunk] = []
        for symbol in symbols:
            header = (
                f"kind: {symbol.kind}\n"
                f"name: {symbol.name}\n"
                f"signature: {symbol.signature}\n"
                f"file: {symbol.file_path}\n"
                f"symbol_line_range: {symbol.start_line}-{symbol.end_line}\n"
            )
            source_prefix = f"{header}\ndocstring:\n{symbol.docstring}\n\nsource:\n"
            composed = f"{source_prefix}{symbol.source}"
            text_parts = self._chunk_text_with_offsets(composed)
            for idx, (text, chunk_start, chunk_end) in enumerate(text_parts):
                start_line, end_line = self._source_line_range(
                    symbol,
                    source_offset=len(source_prefix),
                    chunk_start=chunk_start,
                    chunk_end=chunk_end,
                )
                chunk_id = (
                    f"{symbol.file_path}:{symbol.start_line}:{symbol.end_line}:"
                    f"{symbol.kind}:{symbol.name}:{idx}"
                )
                output.append(
                    CodeChunk(
                        id=chunk_id,
                        text=text,
                        file_path=symbol.file_path,
                        start_line=start_line,
                        end_line=end_line,
                        symbol_name=symbol.name,
                        symbol_kind=symbol.kind,
                    )
                )
        logger.debug("Built %d chunks", len(output))
        return output
