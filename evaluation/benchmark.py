"""
evaluation.benchmark
====================
Run one of the three evaluation pipelines over every discovered example
and aggregate the per-example metrics into a CSV + markdown table.

Pipeline selection
------------------
    --pipeline extraction     source → TTL (+ optional ground-truth compare)
    --pipeline generation     TTL → source (from fixtures/ or prior extractions)
    --pipeline roundtrip      source → TTL → source (same-fw or --target cross-fw)

Discovery
---------
- ``extraction`` and ``roundtrip`` iterate
  ``examples/<framework>/<name>/`` (any subdir containing ``.py`` files).
- ``generation`` iterates all ``.ttl`` files under ``evaluation/fixtures/``
  OR, if ``--from-extraction`` is set, all
  ``output/extraction/<framework>/<name>/extracted.ttl``.

Outputs
-------
    output/<pipeline>/benchmark.csv
    output/<pipeline>/benchmark.md

CLI examples
------------
    python -m evaluation.benchmark --pipeline roundtrip
    python -m evaluation.benchmark --pipeline roundtrip --frameworks crewai
    python -m evaluation.benchmark --pipeline extraction
    python -m evaluation.benchmark --pipeline generation --target-framework langgraph
    python -m evaluation.benchmark --pipeline roundtrip --target langgraph \\
        --only crewai/email-flow
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import Any, Iterable

from evaluation.pipelines import extraction as ext_pipe
from evaluation.pipelines import generation as gen_pipe
from evaluation.pipelines import roundtrip as rt_pipe
from evaluation.reporting import build_row

log = logging.getLogger("oscin.eval.bench")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
FIXTURES_ROOT = PROJECT_ROOT / "evaluation" / "fixtures"
EXTRACTION_OUT = PROJECT_ROOT / "output" / "extraction"
DEFAULT_FRAMEWORKS = ("crewai", "langgraph", "autogen")


# --------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------


def discover_examples(frameworks: Iterable[str]) -> list[tuple[str, Path]]:
    """Return [(framework, example_root), ...] for examples with .py files."""
    found: list[tuple[str, Path]] = []
    for fw in frameworks:
        fw_root = EXAMPLES_ROOT / fw
        if not fw_root.is_dir():
            continue
        for sub in sorted(fw_root.iterdir()):
            if sub.is_dir() and (any(sub.rglob("*.py")) or any(sub.rglob("*.ipynb"))):
                found.append((fw, sub))
    return found


def discover_fixtures() -> list[tuple[str, Path]]:
    """Return [(name, ttl_path), ...] for every .ttl in evaluation/fixtures/."""
    if not FIXTURES_ROOT.is_dir():
        return []
    return [(p.stem, p) for p in sorted(FIXTURES_ROOT.glob("*.ttl"))]


def discover_extraction_outputs() -> list[tuple[str, str, Path]]:
    """Return [(framework, name, ttl_path), ...] of prior extraction outputs."""
    out: list[tuple[str, str, Path]] = []
    if not EXTRACTION_OUT.is_dir():
        return out
    for fw_dir in sorted(EXTRACTION_OUT.iterdir()):
        if not fw_dir.is_dir():
            continue
        for ex_dir in sorted(fw_dir.iterdir()):
            ttl = ex_dir / "extracted.ttl"
            if ttl.is_file():
                out.append((fw_dir.name, ex_dir.name, ttl))
    return out


# --------------------------------------------------------------------
# Per-pipeline runners
# --------------------------------------------------------------------


def _run_extraction_bench(
    frameworks: list[str],
    only: set[str] | None,
    out_root: Path,
) -> list[dict]:
    rows: list[dict] = []
    for fw, ex_root in discover_examples(frameworks):
        key = f"{fw}/{ex_root.name}"
        if only and key not in only:
            continue
        log.info("── extraction: %s ──", key)
        try:
            report = ext_pipe.run_extraction(ex_root, fw, out_root=out_root)
        except Exception as e:
            log.exception("extraction crashed for %s", key)
            report = _crash_report("extraction", fw, ex_root.name, e)
        rows.append(build_row(report))
    return rows


def _run_generation_bench(
    target_framework: str,
    from_extraction: bool,
    only: set[str] | None,
    out_root: Path,
    execute: bool,
    reextract: bool,
) -> list[dict]:
    rows: list[dict] = []
    if from_extraction:
        targets = [(fw, name, ttl) for fw, name, ttl in discover_extraction_outputs()]
    else:
        targets = [(None, name, ttl) for name, ttl in discover_fixtures()]

    for fw, name, ttl in targets:
        key = f"{fw or 'fixture'}/{name}"
        if only and key not in only:
            continue
        log.info("── generation (%s): %s ──", target_framework, key)
        try:
            report = gen_pipe.run_generation(
                ttl=ttl,
                fixture=None,
                target_framework=target_framework,
                execute=execute,
                reextract=reextract,
                out_root=out_root,
                name=name,
            )
        except Exception as e:
            log.exception("generation crashed for %s", key)
            report = _crash_report("generation", target_framework, name, e)
        rows.append(build_row(report))
    return rows


def _run_roundtrip_bench(
    frameworks: list[str],
    target_framework: str | None,
    only: set[str] | None,
    skip_execution: bool,
    execution_timeout: float,
    out_root: Path,
) -> list[dict]:
    rows: list[dict] = []
    for fw, ex_root in discover_examples(frameworks):
        key = f"{fw}/{ex_root.name}"
        if only and key not in only:
            continue
        log.info("── roundtrip: %s (target=%s) ──",
                 key, target_framework or fw)
        try:
            report = rt_pipe.run_roundtrip(
                ex_root,
                fw,
                target_framework=target_framework,
                skip_execution=skip_execution,
                execution_timeout=execution_timeout,
                out_root=out_root,
            )
        except Exception as e:
            log.exception("roundtrip crashed for %s", key)
            report = _crash_report("roundtrip", fw, ex_root.name, e)
        rows.append(build_row(report))
    return rows


def _crash_report(pipeline: str, fw: str, name: str, exc: Exception) -> dict:
    return {
        "pipeline": pipeline,
        "example": name,
        "framework": fw,
        "target_framework": None,
        "steps": {"driver": {"ok": False, "error": f"{type(exc).__name__}: {exc}"}},
        "metrics": {},
    }


# --------------------------------------------------------------------
# CSV / Markdown rendering
# --------------------------------------------------------------------


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        path.write_text("")
        return
    # Union of all keys, with a stable leading set.
    leading = ["pipeline", "framework", "target_framework", "example"]
    extra: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in leading and k not in extra:
                extra.append(k)
    # "errors" last for readability.
    if "errors" in extra:
        extra.remove("errors")
        extra.append("errors")
    fieldnames = leading + extra
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def _write_markdown(rows: list[dict], path: Path, pipeline: str) -> None:
    display_order_by_pipeline = {
        "extraction": [
            "framework", "example",
            "intrinsic_triples", "intrinsic_individuals", "intrinsic_properties",
            "intrinsic_density",
            "triple_f1", "property_f1", "individual_f1", "fuzzy_avg_score",
        ],
        "generation": [
            "framework", "example",
            "intrinsic_triples", "intrinsic_individuals",
            "syntax_rate", "import_rate",
            "ast_overall_f1", "triple_f1",
        ],
        "roundtrip": [
            "framework", "target_framework", "example",
            "triple_f1", "property_f1", "individual_f1",
            "fuzzy_avg_score", "ast_overall_f1",
            "exec_ok_match", "exec_stdout_overlap",
            "mapping_overall",
        ],
    }
    cols = display_order_by_pipeline.get(pipeline, list(rows[0].keys()) if rows else [])
    out = [f"# OSCIN Benchmark — {pipeline}", ""]
    if not rows:
        out.append("_no rows_")
        path.write_text("\n".join(out) + "\n")
        return
    out.append("| " + " | ".join(cols) + " |")
    out.append("|" + "|".join(["---"] * len(cols)) + "|")
    for r in rows:
        row_vals: list[str] = []
        for c in cols:
            v = r.get(c)
            if v is None:
                row_vals.append("—")
            elif isinstance(v, float):
                row_vals.append(f"{v:.3f}")
            else:
                row_vals.append(str(v))
        out.append("| " + " | ".join(row_vals) + " |")

    err_rows = [r for r in rows if r.get("errors")]
    if err_rows:
        out += ["", "## Errors", ""]
        for r in err_rows:
            out.append(
                f"- **{r.get('framework')}/{r.get('example')}** — {r['errors']}"
            )
    path.write_text("\n".join(out) + "\n")


# --------------------------------------------------------------------
# Top-level
# --------------------------------------------------------------------


def run_benchmark(
    pipeline: str,
    *,
    frameworks: list[str] | None = None,
    target_framework: str | None = None,
    only: set[str] | None = None,
    skip_execution: bool = False,
    execution_timeout: float = 120.0,
    from_extraction: bool = False,
    execute: bool = False,
    reextract: bool = False,
    out_root: Path | None = None,
) -> list[dict]:
    out_root = (out_root or PROJECT_ROOT / "output" / pipeline).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    frameworks = frameworks or list(DEFAULT_FRAMEWORKS)

    if pipeline == "extraction":
        rows = _run_extraction_bench(frameworks, only, out_root)
    elif pipeline == "generation":
        if not target_framework:
            raise ValueError("--target-framework required for generation pipeline")
        rows = _run_generation_bench(
            target_framework, from_extraction, only, out_root, execute, reextract
        )
    elif pipeline == "roundtrip":
        rows = _run_roundtrip_bench(
            frameworks, target_framework, only, skip_execution, execution_timeout, out_root
        )
    else:
        raise ValueError(f"unknown pipeline: {pipeline}")

    _write_csv(rows, out_root / "benchmark.csv")
    _write_markdown(rows, out_root / "benchmark.md", pipeline)
    log.info("wrote %s and %s",
             out_root / "benchmark.csv", out_root / "benchmark.md")
    return rows


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="evaluation.benchmark")
    ap.add_argument("--pipeline", "-p", required=True,
                    choices=["extraction", "generation", "roundtrip"])
    ap.add_argument("--frameworks", nargs="+",
                    default=list(DEFAULT_FRAMEWORKS),
                    choices=list(DEFAULT_FRAMEWORKS))
    ap.add_argument("--target-framework", "-t",
                    choices=list(DEFAULT_FRAMEWORKS), default=None,
                    help="required for generation; optional for cross-fw roundtrip")
    ap.add_argument("--only", nargs="+", default=None,
                    help="restrict to 'fw/name' keys, e.g. crewai/email-flow")
    ap.add_argument("--skip-execution", action="store_true")
    ap.add_argument("--execution-timeout", type=float, default=120.0)
    ap.add_argument("--from-extraction", action="store_true",
                    help="[generation] source TTLs from output/extraction/* instead of fixtures/")
    ap.add_argument("--execute", action="store_true",
                    help="[generation] run generated code")
    ap.add_argument("--reextract", action="store_true",
                    help="[generation] re-extract generated code and pairwise-compare")
    ap.add_argument("--out-root", type=Path, default=None)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    args = _parse_args(argv)
    rows = run_benchmark(
        args.pipeline,
        frameworks=args.frameworks,
        target_framework=args.target_framework,
        only=set(args.only) if args.only else None,
        skip_execution=args.skip_execution,
        execution_timeout=args.execution_timeout,
        from_extraction=args.from_extraction,
        execute=args.execute,
        reextract=args.reextract,
        out_root=args.out_root,
    )
    ok = sum(1 for r in rows if not r.get("errors"))
    print(f"{args.pipeline}: {ok}/{len(rows)} examples clean")


if __name__ == "__main__":
    main()
