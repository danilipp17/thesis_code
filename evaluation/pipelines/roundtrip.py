"""
evaluation.pipelines.roundtrip
==============================
Round-trip pipeline with two clearly-separated modes.

Same-framework  (default)
-------------------------
    source ── extract ──▶ TTL₁ ── generate ──▶ source′ ── extract ──▶ TTL₂

Compares the *same* language on both ends.

Metrics
    - ``ttl_pairwise``      TTL₁ vs TTL₂ (ontology idempotence)
    - ``ttl_fuzzy_match``   TTL₁ vs TTL₂ (tolerant of URI renames)
    - ``ast_diff``          source vs source′
    - ``execution_trace``   source vs source′ (unless ``--skip-execution``)

Cross-framework  (``--target <other_fw>``)
------------------------------------------
    source_A ── extract ──▶ TTL₁ ── generate(B) ──▶ source_B ── extract ──▶ TTL₂

Different languages on each end, so AST/exec comparisons are dropped.

Metrics
    - ``ttl_pairwise``      TTL₁ vs TTL₂
    - ``ttl_fuzzy_match``   TTL₁ vs TTL₂
    - ``mapping_conformance`` (only when {src, tgt} == {crewai, langgraph})

Output
------
    output/roundtrip/<source_framework>/<example>/
        ttl1.ttl, ttl2.ttl, generated/, report.{md,json}

CLI
---
    python -m evaluation.pipelines.roundtrip examples/crewai/email-flow -f crewai
    python -m evaluation.pipelines.roundtrip examples/crewai/email-flow -f crewai -t langgraph
    python -m evaluation.pipelines.roundtrip examples/langgraph/ReAct -f langgraph --skip-execution
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from rdflib import Graph

from evaluation.metrics import (
    ast_diff,
    execution_trace,
    mapping_conformance,
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

log = logging.getLogger("oscin.eval.roundtrip")


def run_roundtrip(
    example_root: Path,
    framework: str,
    *,
    target_framework: str | None = None,
    skip_execution: bool = False,
    execution_timeout: float = 120.0,
    out_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the roundtrip pipeline and return the report dict."""
    example_root = example_root.resolve()
    example_name = example_root.name
    source_dir = resolve_source_dir(example_root)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"source dir not found: {source_dir}")

    target_framework = target_framework or framework
    is_cross = (target_framework != framework)

    out_root = (out_root or PROJECT_ROOT / "output" / "roundtrip").resolve()
    work = out_root / framework / example_name
    work.mkdir(parents=True, exist_ok=True)

    ttl1_path = work / "ttl1.ttl"
    gen_dir = work / "generated"
    ttl2_path = work / "ttl2.ttl"
    ns = default_namespace(example_name)
    system_name = default_system_name(example_name)

    report: dict[str, Any] = {
        "pipeline": "roundtrip",
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

    # --- Step 2: generate TTL₁ → source′
    try:
        run_step(report, "generate", run_oscin, [
            "generate", str(ttl1_path),
            "--target-framework", target_framework,
            "--output-dir", str(gen_dir),
        ], _output_hint=str(gen_dir))
    except StepFailed:
        write_report(report, work)
        return report

    # --- Step 3: extract source′ → TTL₂
    try:
        run_step(report, "extract_2", run_oscin, [
            "extract", str(gen_dir),
            "--framework", target_framework,
            # Use the same system name as TTL₁ so the two graphs share
            # the system URI. Otherwise every triple whose subject is the
            # system (includesAgent, includesTeam, hasTitle, …) mismatches
            # purely on the URI local name, collapsing triple_f1 even when
            # properties/individuals are perfectly preserved.
            "--system-name", system_name,
            "--namespace", ns,
            "--output", str(ttl2_path),
            "--no-report",
        ], _output_hint=str(ttl2_path))
    except StepFailed:
        write_report(report, work)
        return report

    # --- Metrics common to both modes: TTL₁ vs TTL₂
    try:
        g1 = Graph(); g1.parse(str(ttl1_path), format="turtle")
        g2 = Graph(); g2.parse(str(ttl2_path), format="turtle")
        report["metrics"]["ttl_pairwise"] = ttl_pairwise.compute_from_graphs(g1, g2)
        report["metrics"]["ttl_fuzzy_match"] = ttl_fuzzy_match.compute(g1, g2)
    except Exception as e:
        report["metrics"]["ttl_pairwise"] = {
            "metric": "ttl_pairwise",
            "error": f"{type(e).__name__}: {e}",
        }

    # --- Mode-specific metrics
    if is_cross:
        # Cross-framework: only the canonical CF↔LG mapping metric makes sense.
        if {framework, target_framework} == {"crewai", "langgraph"}:
            lg_dir = source_dir if framework == "langgraph" else gen_dir
            cf_dir = source_dir if framework == "crewai" else gen_dir
            direction = "cf_to_lg" if framework == "crewai" else "lg_to_cf"
            report["metrics"]["mapping_conformance"] = mapping_conformance.compute(
                lg_dir, cf_dir, direction=direction
            )
    else:
        # Same-framework: AST diff + execution comparison both make sense.
        report["metrics"]["ast_diff"] = ast_diff.compute(source_dir, gen_dir)
        if skip_execution:
            report["metrics"]["execution_trace"] = {
                "metric": "execution_trace",
                "skipped": True,
            }
        else:
            report["metrics"]["execution_trace"] = execution_trace.compute(
                source_dir, gen_dir, timeout=execution_timeout
            )

    write_report(report, work)
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="evaluation.pipelines.roundtrip")
    ap.add_argument("example_root", type=Path)
    ap.add_argument("--framework", "-f", required=True,
                    choices=["crewai", "langgraph", "autogen"])
    ap.add_argument("--target-framework", "-t",
                    choices=["crewai", "langgraph", "autogen"],
                    default=None,
                    help="set for cross-framework roundtrip")
    ap.add_argument("--skip-execution", action="store_true")
    ap.add_argument("--execution-timeout", type=float, default=120.0)
    ap.add_argument("--out-root", type=Path, default=None)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    args = _parse_args(argv)
    r = run_roundtrip(
        args.example_root,
        args.framework,
        target_framework=args.target_framework,
        skip_execution=args.skip_execution,
        execution_timeout=args.execution_timeout,
        out_root=args.out_root,
    )
    print(f"report: {r['work_dir']}/report.md")


if __name__ == "__main__":
    main()
