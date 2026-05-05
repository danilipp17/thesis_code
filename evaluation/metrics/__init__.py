"""
evaluation.metrics
==================
Metric modules used by the three evaluation pipelines.

Each module exposes a uniform contract:

    NAME: str                                 # short identifier
    def compute(...) -> dict                  # returns result dict
    def row(result: dict) -> dict             # flat fields for benchmark.csv
    def summarize_markdown(result: dict) -> str  # markdown block for reports

Current modules:

- ``ttl_intrinsic``       — single-graph statistics
- ``ttl_pairwise``        — graph vs graph P/R/F1
- ``ttl_fuzzy_match``     — graph vs graph with fuzzy entity alignment
- ``ast_diff``            — source-tree structural P/R/F1 (same language)
- ``syntax_validity``     — does every generated .py parse / imports resolve
- ``execution_trace``     — subprocess run comparison (same language)
- ``mapping_conformance`` — CrewAI Flow ↔ LangGraph canonical rule match

The benchmark aggregator imports each module by name and composes the
CSV row by merging every ``row(result)`` dict.
"""

from evaluation.metrics import (  # noqa: F401
    ast_diff,
    execution_trace,
    extraction_coverage,
    mapping_conformance,
    syntax_validity,
    ttl_fuzzy_match,
    ttl_intrinsic,
    ttl_pairwise,
)

ALL_METRICS = {
    "ttl_intrinsic": ttl_intrinsic,
    "ttl_pairwise": ttl_pairwise,
    "ttl_fuzzy_match": ttl_fuzzy_match,
    "ast_diff": ast_diff,
    "syntax_validity": syntax_validity,
    "execution_trace": execution_trace,
    "mapping_conformance": mapping_conformance,
    "extraction_coverage": extraction_coverage,
}
