from mana_agent.analysis.chunker import CodeChunker
from mana_agent.analysis.models import CodeSymbol


def test_chunker_splits_with_overlap() -> None:
    symbol = CodeSymbol(
        kind="function",
        name="big",
        signature="def big():",
        docstring="doc",
        file_path="/tmp/a.py",
        start_line=1,
        end_line=200,
        source="x" * 5000,
    )
    chunker = CodeChunker(max_chars=1000, overlap=100)
    chunks = chunker.build_chunks([symbol])

    assert len(chunks) > 1
    assert chunks[0].file_path == "/tmp/a.py"
    assert chunks[0].id != chunks[1].id


def test_chunker_reports_the_source_lines_covered_by_each_text_slice() -> None:
    source = "".join(f"line_{line:02d} = {line}\n" for line in range(1, 41))
    symbol = CodeSymbol(
        kind="module",
        name="a.py",
        signature="module a.py",
        docstring="",
        file_path="/tmp/a.py",
        start_line=1,
        end_line=40,
        source=source,
    )

    chunks = CodeChunker(max_chars=180, overlap=30).build_chunks([symbol])

    assert len(chunks) > 1
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 40
    assert all(1 <= chunk.start_line <= chunk.end_line <= 40 for chunk in chunks)
    assert any(chunk.start_line > 1 for chunk in chunks[1:])
    assert len({(chunk.start_line, chunk.end_line) for chunk in chunks}) > 1
    assert "symbol_line_range: 1-40" in chunks[0].text
