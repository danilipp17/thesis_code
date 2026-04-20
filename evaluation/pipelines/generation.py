"""
evaluation.pipelines.generation
===============================
Generation-only pipeline: TTL → source code + metrics.

Input modes
-----------
1. ``--ttl path/to/input.ttl``                 (arbitrary TTL file)
2. ``--fixture NAME``                          (resolves to evaluation/fixtures/NAME.ttl)

Pipeline
--------
    input.ttl ── generate ──▶ <target_fw>/main.py

Metrics
-------
- ``syntax_validity``   — every generated .py parses; imports resolvable (always).
- ``ttl_intrinsic``     — snapshot of the input TTL (always).
- ``ast_diff``          — vs a reference source tree if ``--reference-source`` given.
- ``execution_trace``   — if ``--execute`` flag is set (requires .env for API keys).
- ``ttl_pairwise``      — vs a re-extraction if ``--reextract`` is set.

Output
------
    output/generation/<target_framework>/<name>/
        generated/
        report.{md,json}

CLI
---
    python -m evaluation.pipelines.generation \\
        --ttl output/extraction/crewai/email-flow/extracted.ttl \\
        --target-framework langgraph

    python -m evaluation.pipelines.generation \\
        --fixture custom_system --target-framework crewai
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from evaluation.metrics import (
    ast_diff,
    execution_trace,
    syntax_validity,
    ttl_intrinsic,
    ttl_pairwise,
)
from evaluation.pipelines._common import (
    PROJECT_ROOT,
    StepFailed,
    run_oscin,
    run_step,
)
from evaluation.reporting import write_report

log = logging.getLogger("oscin.eval.generation")

FIXTURES_DIR = PROJECT_ROOT / "evaluation" / "fixtures"


def _resolve_input(
    ttl: Path | None, fixture: str | None
) -> tuple[Path, str]:
    """Resolve the input TTL path and derive a short name for the report."""
    if ttl is not None:
        return ttl.resolve(), ttl.stem
    if fixture is not None:
        path = (FIXTURES_DIR / f"{fixture}.ttl").resolve()
        if not path.is_file():
            raise FileNotFoundError(
                f"fixture not found: {path} "
                f"(drop a .ttl file into evaluation/fixtures/ named '{fixture}.ttl')"
            )
        return path, fixture
    raise ValueError("must provide either --ttl or --fixture")


def run_generation(
    *,
    ttl: Path | None,
    fixture: str | None,
    target_framework: str,
    reference_source: Path | None = None,
    execute: bool = False,
    reextract: bool = False,
    out_root: Path | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Execute the generation pipeline and return the report dict."""
    ttl_path, derived_name = _resolve_input(ttl, fixture)
    name = name or derived_name

    out_root = (out_root or PROJECT_ROOT / "output" / "generation").resolve()
    work = out_root / target_framework / name
    work.mkdir(parents=True, exist_ok=True)

    gen_dir = work / "generated"

    report: dict[str, Any] = {
        "pipeline": "generation",
        "example": name,
        "framework": target_framework,       # in generation, framework == target
        "target_framework": target_framework,
        "source_dir": str(ttl_path),         # reuse field for render
        "work_dir": str(work),
        "input_ttl": str(ttl_path),
        "steps": {},
        "metrics": {},
    }

    # Intrinsic of the input (so the report shows what we fed the generator)
    report["metrics"]["ttl_intrinsic"] = ttl_intrinsic.compute(ttl_path)

    # Step: generate
    try:
        run_step(
            report,
            "generate",
            run_oscin,
            [
                "generate", str(ttl_path),
                "--target-framework", target_framework,
                "--output-dir", str(gen_dir),
            ],
            _output_hint=str(gen_dir),
        )
    except StepFailed:
        write_report(report, work)
        return report

    # Metrics
    report["metrics"]["syntax_validity"] = syntax_validity.compute(gen_dir)

    if reference_source is not None:
        report["metrics"]["ast_diff"] = ast_diff.compute(reference_source, gen_dir)

    if reextract:
        ttl2 = work / "reextracted.ttl"
        try:
            run_step(
                report,
                "reextract",
                run_oscin,
                [
                    "extract", str(gen_dir),
                    "--framework", target_framework,
                    "--system-name", f"{name}_reextract",
                    "--namespace", f"http://example.org/{name}#",
                    "--output", str(ttl2),
                    "--no-report",
                ],
                _output_hint=str(ttl2),
            )
            report["metrics"]["ttl_pairwise"] = ttl_pairwise.compute(
                ttl_path, ttl2
            )
        except StepFailed:
            pass

    if execute:
        if reference_source is not None:
            report["metrics"]["execution_trace"] = execution_trace.compute(
                reference_source, gen_dir, timeout=120.0
            )
        else:
            # Only run the generated side; compare against its own success.
            entry = execution_trace.find_entry(gen_dir)
            if entry is not None:
                run_result = execution_trace.run_target(entry, timeout=120.0)
                report["metrics"]["execution_trace"] = {
                    "metric": "execution_trace",
                    "ref_ok": None,
                    "cand_ok": bool(run_result.get("ok")),
                    "ok_match": None,
                    "error_match": None,
                    "cand_error": run_result.get("error"),
                    "stdout_overlap": None,
                    "duration_ratio": None,
                    "cand_entry": str(entry),
                }

    write_report(report, work)
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="evaluation.pipelines.generation")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--ttl", type=Path, help="input TTL path")
    src.add_argument("--fixture", type=str,
                     help="fixture name under evaluation/fixtures/")
    ap.add_argument("--target-framework", "-t", required=True,
                    choices=["crewai", "langgraph", "autogen"])
    ap.add_argument("--reference-source", type=Path, default=None,
                    help="source dir to AST-diff against (optional)")
    ap.add_argument("--execute", action="store_true",
                    help="run the generated code (needs .env for API keys)")
    ap.add_argument("--reextract", action="store_true",
                    help="extract generated code back to TTL and pairwise-compare")
    ap.add_argument("--name", type=str, default=None,
                    help="override report name (defaults to TTL stem / fixture name)")
    ap.add_argument("--out-root", type=Path, default=None)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    args = _parse_args(argv)
    r = run_generation(
        ttl=args.ttl,
        fixture=args.fixture,
        target_framework=args.target_framework,
        reference_source=args.reference_source,
        execute=args.execute,
        reextract=args.reextract,
        out_root=args.out_root,
        name=args.name,
    )
    print(f"report: {r['work_dir']}/report.md")


if __name__ == "__main__":
    main()
