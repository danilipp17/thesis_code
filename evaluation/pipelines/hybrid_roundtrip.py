"""
evaluation.pipelines.hybrid_roundtrip
======================================
Hybrid deterministic + LLM fixup round-trip pipeline.

Flow:
    source → AST extract → TTL₁ → deterministic generate → skeleton
                                                        → LLM fixup → source′
                                                       → AST extract → TTL₂

Compares:
    - TTL₁ vs TTL₂  (ontology idempotence after fixup)
    - source vs source′ (AST diff, syntax validity, execution trace)

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    May 2026
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rdflib import Graph

from evaluation.metrics import (
    ast_diff,
    execution_trace,
    syntax_validity,
    ttl_fuzzy_match,
    ttl_pairwise,
)
from evaluation.pipelines._common import (
    PROJECT_ROOT,
    StepFailed,
    default_namespace,
    default_system_name,
    resolve_source_dir,
    run_oscin,
    run_step,
)
from evaluation.reporting import write_report
from oscin.llm_fixup import run_llm_fixup

log = logging.getLogger("oscin.eval.hybrid_roundtrip")


def run_hybrid_roundtrip(
    example_root: Path,
    framework: str,
    *,
    target_framework: str | None = None,
    skip_execution: bool = False,
    execution_timeout: float = 120.0,
    llm_provider: str = "openai",
    llm_model: str | None = None,
    out_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the hybrid deterministic + LLM fixup roundtrip pipeline.

    Parameters
    ----------
    example_root : Path
        Path to the example directory.
    framework : str
        Source framework (crewai, langgraph, autogen).
    target_framework : str | None
        Target framework for cross-framework generation. If None, same as source.
    skip_execution : bool
        Whether to skip the execution trace metric.
    execution_timeout : float
        Timeout for execution trace in seconds.
    llm_provider : str
        LLM provider for the fixup step (openai or anthropic).
    llm_model : str | None
        LLM model name for the fixup step.
    out_root : Path | None
        Root directory for output files.

    Returns
    -------
    dict[str, Any]
        Report dictionary with metrics and step information.
    """
    example_root = example_root.resolve()
    example_name = example_root.name
    source_dir = resolve_source_dir(example_root)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"source dir not found: {source_dir}")

    target_framework = target_framework or framework
    is_cross = target_framework != framework

    out_root = (out_root or PROJECT_ROOT / "output" / "hybrid_roundtrip").resolve()
    work = out_root / framework / example_name
    if is_cross:
        work = out_root / f"{framework}_to_{target_framework}" / example_name
    work.mkdir(parents=True, exist_ok=True)

    ttl1_path = work / "ttl1.ttl"
    skeleton_dir = work / "generated"
    fixed_dir = work / "generated_fixed"
    ttl2_path = work / "ttl2.ttl"
    ns = default_namespace(example_name)
    system_name = default_system_name(example_name)

    report: dict[str, Any] = {
        "pipeline": "hybrid_roundtrip",
        "mode": "cross_framework" if is_cross else "same_framework",
        "example": example_name,
        "framework": framework,
        "target_framework": target_framework,
        "source_dir": str(source_dir),
        "work_dir": str(work),
        "steps": {},
        "metrics": {},
    }

    # --- Step 1: extract source → TTL₁
    try:
        run_step(report, "extract_1", run_oscin, [
            "extract", str(source_dir),
            "--framework", framework,
            "--system-name", system_name,
            "--namespace", ns,
            "--output", str(ttl1_path),
            "--no-report",
        ], _output_hint=str(ttl1_path))
    except StepFailed:
        write_report(report, work)
        return report

    # --- Step 2: deterministic generate TTL₁ → skeleton code
    try:
        run_step(report, "generate_skeleton", run_oscin, [
            "generate", str(ttl1_path),
            "--target-framework", target_framework,
            "--output-dir", str(skeleton_dir),
        ], _output_hint=str(skeleton_dir))
    except StepFailed:
        write_report(report, work)
        return report

    # --- Step 3: LLM fixup skeleton + TTL₁ → fixed source code
    try:
        fixed_result = run_llm_fixup(
            generated_dir=skeleton_dir,
            ttl_file=ttl1_path,
            target_framework=target_framework,
            output_dir=fixed_dir,
            provider=llm_provider,
            model=llm_model,
        )
        report["steps"]["llm_fixup"] = {
            "status": "ok",
            "output_dir": str(fixed_result),
        }
    except Exception as e:
        report["steps"]["llm_fixup"] = {
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
        }
        write_report(report, work)
        return report

    # --- Step 4: extract fixed source → TTL₂
    try:
        run_step(report, "extract_2", run_oscin, [
            "extract", str(fixed_dir),
            "--framework", target_framework,
            "--system-name", system_name,
            "--namespace", ns,
            "--output", str(ttl2_path),
            "--no-report",
        ], _output_hint=str(ttl2_path))
    except StepFailed:
        write_report(report, work)
        return report

    # --- Metrics: TTL pairwise + fuzzy
    try:
        g1 = Graph()
        g1.parse(str(ttl1_path), format="turtle")
        g2 = Graph()
        g2.parse(str(ttl2_path), format="turtle")
        report["metrics"]["ttl_pairwise"] = ttl_pairwise.compute_from_graphs(g1, g2)
        report["metrics"]["ttl_fuzzy_match"] = ttl_fuzzy_match.compute(g1, g2)
    except Exception as e:
        report["metrics"]["ttl_pairwise"] = {
            "metric": "ttl_pairwise",
            "error": f"{type(e).__name__}: {e}",
        }

    # --- Metrics: syntax validity of fixed code
    try:
        report["metrics"]["syntax_validity"] = syntax_validity.compute(fixed_dir)
    except Exception as e:
        report["metrics"]["syntax_validity"] = {
            "metric": "syntax_validity",
            "error": f"{type(e).__name__}: {e}",
        }

    # --- Mode-specific metrics
    if not is_cross:
        # Same-framework: AST diff and execution trace make sense
        try:
            report["metrics"]["ast_diff"] = ast_diff.compute(source_dir, fixed_dir)
        except Exception as e:
            report["metrics"]["ast_diff"] = {
                "metric": "ast_diff",
                "error": f"{type(e).__name__}: {e}",
            }

        if skip_execution:
            report["metrics"]["execution_trace"] = {
                "metric": "execution_trace",
                "skipped": True,
            }
        else:
            try:
                report["metrics"]["execution_trace"] = execution_trace.compute(
                    source_dir, fixed_dir, timeout=execution_timeout
                )
            except Exception as e:
                report["metrics"]["execution_trace"] = {
                    "metric": "execution_trace",
                    "error": f"{type(e).__name__}: {e}",
                }

    write_report(report, work)
    return report