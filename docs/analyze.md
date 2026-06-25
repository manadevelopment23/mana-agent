# Project Analysis

## Scope
This document summarizes the repository based on the analyzed `src/` Python code and the top-level project docs.

## High-level purpose
`mana-agent` is a CLI for repository analysis, question answering, and coding-agent workflows. The README states it indexes a project, performs static and dependency analysis, generates reports, answers repo questions with context, and supports an interactive chat/coding flow. `analyze` writes artifacts into `.mana/`, including JSON, Markdown, HTML, DOT, and GraphML outputs. [README.md:1-272]

## Main code areas observed
- `src/mana_agent/services/`
  - Orchestrates analysis, reporting, dependency collection, describe flows, structure inspection, and vulnerability scanning.
- `src/mana_agent/analysis/`
  - Contains the static Python analyzer, code chunking, and data models for findings/chunks/reports.
- `src/mana_agent/llm/`
  - Contains the LLM analyze chain and prompt/run logging helpers.
- `src/mana_agent/commands/`
  - CLI entrypoints and output/UI helpers.
- `src/mana_agent/tools/` and `src/mana_agent/utils/`
  - Repository tool wrappers, write/apply utilities, discovery, logging, policy, and I/O helpers.

The directory layout from the repository root aligns with the README’s documented architecture. [README.md:205-229]

## Static analysis pipeline
`AnalyzeService` is responsible for file-level static analysis. It resolves the target path, collects Python files with `iter_python_files`, and runs `PythonStaticAnalyzer.analyze_file` either sequentially or via `ProcessPoolExecutor` depending on file count. Findings are sorted by file path, line, column, and rule ID before return. [src/mana_agent/services/analyze_service.py:1-57]

`PythonStaticAnalyzer` currently checks each Python file for:
- wildcard imports,
- unused imports,
- missing module/class/function docstrings,
- deep nesting beyond 3 control-structure levels. [src/mana_agent/analysis/checks.py:1-156]

The finding model stores rule ID, severity, message, file location, and optional architecture/technology summaries. [src/mana_agent/analysis/models.py:28-47]

## LLM analysis pipeline
`AnalyzeChain` builds a chat prompt from system and human templates, initializes `ChatOpenAI`, and invokes the chain with file source plus serialized static findings. It then parses the LLM response as JSON and normalizes each item into a `Finding`. [src/mana_agent/llm/analyze_chain.py:1-161]

Important behavior observed:
- The code includes retry logic around LLM invocation with exponential backoff and up to 100 retries. [src/mana_agent/llm/analyze_chain.py:60-93]
- Non-dict items, empty messages, invalid severities, and malformed positions are normalized or dropped. [src/mana_agent/llm/analyze_chain.py:28-58]
- LLM run telemetry is logged through `LlmRunLogger`. [src/mana_agent/llm/analyze_chain.py:94-161]

## Report generation
`ReportService.generate()` is the central orchestrator. It:
1. Finds the project root.
2. Builds dependencies/inventory.
3. Collects static and optional LLM findings.
4. Calls describe and structure services.
5. Runs vulnerability scanning.
6. Optionally synthesizes deep flow payloads.
7. Produces a `ProjectAuditReport` containing meta, summary, project summary, dependencies, findings, security, and warnings. [src/mana_agent/services/report_service.py:1-745]

The rendered markdown includes sections for:
- overview,
- technologies and dependencies,
- project summary,
- file structure or file summaries,
- bugs and errors,
- OSV security findings,
- warnings and limitations. [src/mana_agent/services/report_service.py:490-745]

## Data model structure
The repository uses dataclasses in `analysis/models.py` to carry structured analysis outputs. Notable types include:
- `CodeSymbol` and `CodeChunk` for symbol/chunk analysis,
- `Finding` and `SearchHit` for issues and search results,
- `ProjectStructureReport`, `DependencyGraphReport`, `DescribeReport`, and `ProjectAuditReport`-related objects for higher-level reporting. [src/mana_agent/analysis/models.py:1-350]

`DependencyGraphReport` also exposes `to_dot()` and `to_graphml()` helpers for graph exports. [src/mana_agent/analysis/models.py:180-244]

## Code chunking
`CodeChunker` produces chunk text from `CodeSymbol` objects. It composes a text block with symbol metadata, docstring, and source, then splits it into overlapping segments if needed. This appears intended for downstream indexing or LLM context packaging. [src/mana_agent/analysis/chunker.py:1-61]

## Repository-level conclusions
- The project is centered on repository inspection, analysis, and LLM-assisted reporting.
- Python static analysis is present and explicit; other language support appears to exist in parser/service scaffolding, but the observed concrete static checker is Python-only. [README.md:205-229] [src/mana_agent/analysis/checks.py:1-156]
- Reporting is layered: dependency, findings, describe, structure, and security signals are merged into one audit artifact. [src/mana_agent/services/report_service.py:1-745]
- The `analyze` CLI output is designed to generate both machine-readable and human-readable artifacts under `.mana/`. [README.md:77-118]

## Notable implementation risk
One high-risk area is `AnalyzeChain.run()`: the retry loop uses up to 100 attempts with exponential backoff and may sleep for long periods on repeated failures. That is concrete behavior in the source, not just a theoretical concern. [src/mana_agent/llm/analyze_chain.py:60-93]
