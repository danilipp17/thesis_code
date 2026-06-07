"""
evaluation.pipelines.extraction
===============================
Extraction-only pipeline: source code → TTL + metrics.

Pipeline
--------
    source/ ── extract ──▶ TTL

Metrics
-------
- ``ttl_intrinsic``     — counts/density of the produced TTL (always).
- ``ttl_pairwise``      — vs ground-truth TTL if present (optional).
- ``ttl_fuzzy_match``   — vs ground-truth TTL if present (optional).

A ground-truth TTL is auto-detected if a file
``examples/<fw>/<name>/ground_truth.ttl`` exists, or it can be passed
explicitly via ``--ground-truth``.

Output
------
    output/extraction/<framework>/<example>/
        extracted.ttl
        report.{md,json}

CLI
---
    python -m evaluation.pipelines.extraction examples/crewai/email-flow -f crewai
    python -m evaluation.pipelines.extraction examples/crewai/email-flow \\
        -f crewai --ground-truth path/to/gt.ttl
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from evaluation.metrics import ttl_fuzzy_match, ttl_intrinsic, ttl_pairwise
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

log = logging.getLogger("oscin.eval.extraction")


def _discover_ground_truth(example_root: Path) -> Path | None:
    candidate = example_root / "ground_truth.ttl"
    return candidate if candidate.is_file() else None


def run_extraction(
    example_root: Path,
    framework: str,
    *,
    ground_truth: Path | None = None,
    out_root: Path | None = None,
    system_name: str | None = None,
    namespace: str | None = None,
) -> dict[str, Any]:
    """Execute the extraction pipeline and return the report dict.

    ``system_name`` and ``namespace`` default to values derived from
    ``example_root.name``. Pass them explicitly when the example lives
    under a path whose leaf is not the desired system name (e.g.\\
    ``examples/parallel/<family>/<framework>/`` where the family — not
    the framework — should be the system identity).
    """
    example_root = example_root.resolve()
    example_name = example_root.name
    source_dir = resolve_source_dir(example_root)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"source dir not found: {source_dir}")

    out_root = (out_root or PROJECT_ROOT / "output" / "extraction").resolve()
    work = out_root / framework / example_name
    work.mkdir(parents=True, exist_ok=True)

    ttl_path = work / "extracted.ttl"

    if ground_truth is None:
        ground_truth = _discover_ground_truth(example_root)

    effective_system_name = system_name or default_system_name(example_name)
    effective_namespace = namespace or default_namespace(example_name)

    report: dict[str, Any] = {
        "pipeline": "extraction",
        "example": example_name,
        "framework": framework,
        "target_framework": None,
        "source_dir": str(source_dir),
        "work_dir": str(work),
        "ground_truth": str(ground_truth) if ground_truth else None,
        "system_name": effective_system_name,
        "namespace": effective_namespace,
        "steps": {},
        "metrics": {},
    }

    # Step: extract
    try:
        run_step(
            report,
            "extract",
            run_oscin,
            [
                "extract", str(source_dir),
                "--framework", framework,
                "--system-name", effective_system_name,
                "--namespace", effective_namespace,
                "--output", str(ttl_path),
                "--no-report",
            ],
            _output_hint=str(ttl_path),
        )
    except StepFailed:
        write_report(report, work)
        return report

    # Metrics
    report["metrics"]["ttl_intrinsic"] = ttl_intrinsic.compute(ttl_path)
    if ground_truth and ground_truth.is_file():
        report["metrics"]["ttl_pairwise"] = ttl_pairwise.compute(ground_truth, ttl_path)
        try:
            from rdflib import Graph
            g_ref = Graph(); g_ref.parse(str(ground_truth), format="turtle")
            g_cand = Graph(); g_cand.parse(str(ttl_path), format="turtle")
            report["metrics"]["ttl_fuzzy_match"] = ttl_fuzzy_match.compute(g_ref, g_cand)
        except Exception as e:
            report["metrics"]["ttl_fuzzy_match"] = {
                "metric": "ttl_fuzzy_match",
                "error": f"{type(e).__name__}: {e}",
            }

    write_report(report, work)
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="evaluation.pipelines.extraction")
    ap.add_argument("example_root", type=Path)
    ap.add_argument("--framework", "-f", required=True,
                    choices=["crewai", "langgraph", "autogen"])
    ap.add_argument("--ground-truth", type=Path, default=None)
    ap.add_argument("--out-root", type=Path, default=None)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    args = _parse_args(argv)
    r = run_extraction(
        args.example_root,
        args.framework,
        ground_truth=args.ground_truth,
        out_root=args.out_root,
    )
    print(f"report: {r['work_dir']}/report.md")


if __name__ == "__main__":
    main()
