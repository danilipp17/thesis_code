# Agents Guide — OSCIN Extractor

Quick orientation for future agents working in this repo.

## What this repo is
- OSCIN: bidirectional transformation between agentic framework source code and a shared OWL ontology.
- Frameworks: CrewAI, LangGraph, AutoGen.
- Thesis project (TU Wien, 2026).

## Core architecture
- Parsers (AST + framework-specific) -> intermediate IR -> ontology TTL.
- Reader + generators take TTL and emit framework source.
- Evaluation harness compares TTL/AST outputs across pipelines.

## Key entry points
- GUI: `streamlit run gui/app.py`
- CLI (installed): `oscin` (see `README.md`)

## Pipelines (evaluation/)
- Extraction: `evaluation/pipelines/extraction.py` (source -> TTL)
- Generation: `evaluation/pipelines/generation.py` (TTL -> source)
- Roundtrip: `evaluation/pipelines/roundtrip.py` (source -> TTL -> source)
- Hybrid roundtrip: `evaluation/pipelines/hybrid_roundtrip.py` (deterministic + LLM fixup)

## Metrics
- Core TTL metrics: `oscin/evaluator.py`
- Metric adapters: `evaluation/metrics/*.py`
- Metric registry: `evaluation/metrics/__init__.py` (ALL_METRICS)

## LLM components
- LLM extraction: `oscin/llm_extractor.py` (prompt: `oscin/prompts/llm_extraction.md`)
- LLM generation: `oscin/llm_generator.py` (prompt: `oscin/prompts/llm_generation.md`)
- LLM fixup: `oscin/llm_fixup.py` (prompt: `oscin/prompts/llm_fixup.md`)

## Repo layout (high signal)
- `ontology/agentoscin.ttl` (OWL schema)
- `oscin/` (parsers, IR, populator, reader, generators)
- `examples/` (input examples per framework)
- `evaluation/` (pipelines, metrics, fixtures, mappings)
- `gui/` (Streamlit app)

## Outputs
- GUI outputs: `output/gui/<pipeline>/...`
- CLI outputs: `output/<pipeline>/...`

## Environment
- `.env` for OpenAI / Anthropic keys (required for LLM features)

## Common tasks
- Run GUI: `streamlit run gui/app.py`
- Run extraction: `python -m evaluation.pipelines.extraction examples/crewai/email-flow -f crewai`
- Run roundtrip: `python -m evaluation.pipelines.roundtrip examples/crewai/email-flow -f crewai`
- Benchmark: `python -m evaluation.benchmark --pipeline <extraction|generation|roundtrip>`

## When adding a metric
- Create `evaluation/metrics/<name>.py` implementing NAME, compute, row, summarize_markdown.
- Register in `evaluation/metrics/__init__.py`.
