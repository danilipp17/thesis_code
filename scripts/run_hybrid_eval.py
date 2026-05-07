"""
run_hybrid_eval.py
==================
Three-way generation approach comparison:
  1. Deterministic (AST) generation only  — structural skeleton, won't run
  2. Hybrid (deterministic + LLM fixup)   — skeleton + LLM fills gaps
  3. Pure LLM end-to-end                  — LLM does everything

Runs same-framework roundtrips for all examples and produces a
side-by-side comparison table.

Output: output/eval_hybrid/
"""

from __future__ import annotations

import json
import logging
import statistics
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from rdflib import Graph

from evaluation.pipelines._common import (
    PROJECT_ROOT,
    default_namespace,
    default_system_name,
    resolve_source_dir,
    run_oscin,
)
from evaluation.pipelines.roundtrip import run_roundtrip
from evaluation.pipelines.hybrid_roundtrip import run_hybrid_roundtrip
from evaluation.metrics import ast_diff, syntax_validity, ttl_pairwise, ttl_fuzzy_match
from oscin.llm_extractor import run_llm_extraction
from oscin.llm_generator import run_llm_generation
from oscin.evaluator import compute_pairwise

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
log = logging.getLogger("eval_hybrid")

OUT_ROOT = ROOT / "output" / "eval_hybrid"

CREWAI_EXAMPLES = [
    "academic-research-flow",
    "code-review",
    "comprehensive",
    "content-pipeline",
    "email-flow",
    "self-eval-loop-flow",
    "tech-blog",
    "unseen-hiring-pipeline",
]

LANGGRAPH_EXAMPLES = [
    "ReAct",
    "drafter",
    "joke",
    "memoryagent",
    "ragagent",
    "research-assistant",
    "tech-blog",
    "unseen-customer-support",
]

AUTOGEN_EXAMPLES = [
    "code-review",
    "company-research",
    "content-pipeline",
    "data-analysis-0.4",
    "literature-review",
    "tech-blog",
    "travel-planning",
    "unseen-debate",
]

ALL_EXAMPLES = (
    [("crewai", ex) for ex in CREWAI_EXAMPLES]
    + [("langgraph", ex) for ex in LANGGRAPH_EXAMPLES]
    + [("autogen", ex) for ex in AUTOGEN_EXAMPLES]
)

LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o"


def resolve_example_root(fw: str, name: str) -> Path:
    return ROOT / "examples" / fw / name


def load_graph(path: Path) -> Graph | None:
    if not path.exists():
        return None
    g = Graph()
    try:
        g.parse(str(path), format="turtle")
        return g
    except Exception:
        return None


def safe_run(label: str, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        log.error(f"  FAILED [{label}]: {e}")
        traceback.print_exc()
        return None


def _extract_metrics(report: dict | None) -> dict:
    """Extract comparable metrics from a roundtrip report."""
    if report is None:
        return {"status": "error"}

    metrics = report.get("metrics", {})
    pw = metrics.get("ttl_pairwise", {})
    fuzzy = metrics.get("ttl_fuzzy_match", {})
    ast = metrics.get("ast_diff", {})
    syn = metrics.get("syntax_validity", {})
    exe = metrics.get("execution_trace", {})

    return {
        "status": "ok",
        "triple_f1": pw.get("triple_f1"),
        "aligned_f1": pw.get("aligned_triple_f1"),
        "property_f1": pw.get("property_f1"),
        "individual_f1": pw.get("individual_f1"),
        "literal_overlap": pw.get("literal_overlap"),
        "fuzzy_avg": fuzzy.get("avg_score"),
        "ast_f1": (ast.get("overall") or {}).get("f1") if isinstance(ast, dict) and "error" not in ast else None,
        "syntax_rate": syn.get("syntax_rate"),
        "import_rate": syn.get("import_rate"),
        "exec_ok": exe.get("ok_match") if isinstance(exe, dict) and not exe.get("skipped") else None,
        "exec_stdout_overlap": exe.get("stdout_overlap") if isinstance(exe, dict) and not exe.get("skipped") else None,
    }


# ===================================================================
# PHASE 1: Same-framework roundtrip — all 3 approaches
# ===================================================================

def run_same_fw_comparison():
    """Run same-framework comparison across all 3 generation approaches."""
    log.info("=" * 60)
    log.info("PHASE 1: Same-Framework 3-Way Comparison")
    log.info("=" * 60)

    results = []

    for fw, ex in ALL_EXAMPLES:
        log.info(f"\n  [{fw}] {ex}")
        example_root = resolve_example_root(fw, ex)

        row = {"framework": fw, "example": ex}

        # --- Approach 1: Deterministic (AST) roundtrip ---
        log.info("    1/3 Deterministic roundtrip...")
        det_report = safe_run(
            f"det {fw}/{ex}",
            run_roundtrip,
            example_root, fw,
            skip_execution=True,
            out_root=OUT_ROOT / "deterministic",
        )
        row["deterministic"] = _extract_metrics(det_report)

        # --- Approach 2: Hybrid (deterministic + LLM fixup) roundtrip ---
        log.info("    2/3 Hybrid (deterministic + LLM fixup) roundtrip...")
        hybrid_report = safe_run(
            f"hybrid {fw}/{ex}",
            run_hybrid_roundtrip,
            example_root, fw,
            skip_execution=True,
            llm_provider=LLM_PROVIDER,
            llm_model=LLM_MODEL,
            out_root=OUT_ROOT / "hybrid",
        )
        row["hybrid"] = _extract_metrics(hybrid_report)

        # --- Approach 3: Pure LLM roundtrip ---
        log.info("    3/3 Pure LLM roundtrip...")
        llm_result = _run_pure_llm_same_fw(fw, ex)
        row["llm"] = llm_result

        results.append(row)
        _log_row(row)

    # Aggregate and write
    _write_results(results, OUT_ROOT / "same_fw_comparison")
    return results


def _run_pure_llm_same_fw(fw: str, ex: str) -> dict:
    """Run pure LLM same-framework roundtrip for one example."""
    example_root = resolve_example_root(fw, ex)
    source_dir = resolve_source_dir(example_root)

    work = OUT_ROOT / "pure_llm" / fw / ex
    work.mkdir(parents=True, exist_ok=True)

    ttl1_path = work / "ttl1_llm.ttl"
    gen_dir = work / "generated"
    ttl2_path = work / "ttl2.ttl"

    ns = default_namespace(ex)
    system_name = default_system_name(ex)

    # Step 1: LLM extraction
    if not ttl1_path.exists():
        try:
            run_llm_extraction(
                source_dir=source_dir,
                output_path=ttl1_path,
                instance_namespace=ns,
                provider=LLM_PROVIDER,
                model=LLM_MODEL,
            )
        except Exception as e:
            return {"status": "error", "error": f"LLM extract: {e}"}

    # Step 2: LLM generation
    if not gen_dir.exists() or not list(gen_dir.glob("**/*.py")):
        try:
            run_llm_generation(
                ttl_file=ttl1_path,
                output_dir=gen_dir,
                target_framework=fw,
                provider=LLM_PROVIDER,
                model=LLM_MODEL,
            )
        except Exception as e:
            return {"status": "error", "error": f"LLM generate: {e}"}

    # Step 3: AST re-extraction
    if not ttl2_path.exists():
        try:
            run_oscin([
                "extract", str(gen_dir),
                "--framework", fw,
                "--system-name", system_name,
                "--namespace", ns,
                "--output", str(ttl2_path),
                "--no-report",
            ])
        except Exception as e:
            return {"status": "error", "error": f"Re-extract: {e}"}

    # Step 4: Compare + extra metrics
    g1 = load_graph(ttl1_path)
    g2 = load_graph(ttl2_path)

    if g1 and g2:
        pw = compute_pairwise(g1, g2)
        fuzzy_result = ttl_fuzzy_match.compute(g1, g2)
        syn_result = syntax_validity.compute(gen_dir)
        ast_result = ast_diff.compute(source_dir, gen_dir)

        return {
            "status": "ok",
            "triple_f1": pw.triple_f1,
            "aligned_f1": pw.aligned_triple_f1,
            "property_f1": pw.property_f1,
            "individual_f1": pw.individual_f1,
            "literal_overlap": pw.literal_overlap,
            "fuzzy_avg": fuzzy_result.get("avg_score"),
            "ast_f1": (ast_result.get("overall") or {}).get("f1") if isinstance(ast_result, dict) and "error" not in ast_result else None,
            "syntax_rate": syn_result.get("syntax_rate"),
            "import_rate": syn_result.get("import_rate"),
        }
    else:
        return {"status": "error", "error": "graph parse failed"}


# ===================================================================
# PHASE 2: Cross-framework roundtrip — all 3 approaches
# ===================================================================

def run_cross_fw_comparison():
    """Run cross-framework comparison across all 3 generation approaches."""
    log.info("=" * 60)
    log.info("PHASE 2: Cross-Framework 3-Way Comparison (CrewAI ↔ LangGraph)")
    log.info("=" * 60)

    results = []
    directions = [
        ("crewai", "langgraph", CREWAI_EXAMPLES),
        ("langgraph", "crewai", LANGGRAPH_EXAMPLES),
    ]

    for src_fw, tgt_fw, examples in directions:
        for ex in examples:
            log.info(f"\n  [{src_fw}→{tgt_fw}] {ex}")
            example_root = resolve_example_root(src_fw, ex)
            row = {"direction": f"{src_fw}→{tgt_fw}", "example": ex}

            # --- Approach 1: Deterministic ---
            log.info("    1/3 Deterministic roundtrip...")
            det_report = safe_run(
                f"det {src_fw}→{tgt_fw}/{ex}",
                run_roundtrip,
                example_root, src_fw,
                target_framework=tgt_fw,
                skip_execution=True,
                out_root=OUT_ROOT / "cross_deterministic",
            )
            row["deterministic"] = _extract_metrics(det_report)

            # --- Approach 2: Hybrid ---
            log.info("    2/3 Hybrid roundtrip...")
            hybrid_report = safe_run(
                f"hybrid {src_fw}→{tgt_fw}/{ex}",
                run_hybrid_roundtrip,
                example_root, src_fw,
                target_framework=tgt_fw,
                skip_execution=True,
                llm_provider=LLM_PROVIDER,
                llm_model=LLM_MODEL,
                out_root=OUT_ROOT / "cross_hybrid",
            )
            row["hybrid"] = _extract_metrics(hybrid_report)

            # --- Approach 3: Pure LLM ---
            log.info("    3/3 Pure LLM roundtrip...")
            llm_result = _run_pure_llm_cross_fw(src_fw, tgt_fw, ex)
            row["llm"] = llm_result

            results.append(row)
            _log_row(row)

    _write_results(results, OUT_ROOT / "cross_fw_comparison")
    return results


def _run_pure_llm_cross_fw(src_fw: str, tgt_fw: str, ex: str) -> dict:
    """Run pure LLM cross-framework roundtrip for one example."""
    example_root = resolve_example_root(src_fw, ex)
    source_dir = resolve_source_dir(example_root)

    work = OUT_ROOT / "cross_pure_llm" / f"{src_fw}_to_{tgt_fw}" / ex
    work.mkdir(parents=True, exist_ok=True)

    ttl1_path = work / "ttl1_llm.ttl"
    gen_dir = work / "generated"
    ttl2_path = work / "ttl2.ttl"

    ns = default_namespace(ex)
    system_name = default_system_name(ex)

    if not ttl1_path.exists():
        try:
            run_llm_extraction(
                source_dir=source_dir,
                output_path=ttl1_path,
                instance_namespace=ns,
                provider=LLM_PROVIDER,
                model=LLM_MODEL,
            )
        except Exception as e:
            return {"status": "error", "error": f"LLM extract: {e}"}

    if not gen_dir.exists() or not list(gen_dir.glob("**/*.py")):
        try:
            run_llm_generation(
                ttl_file=ttl1_path,
                output_dir=gen_dir,
                target_framework=tgt_fw,
                provider=LLM_PROVIDER,
                model=LLM_MODEL,
            )
        except Exception as e:
            return {"status": "error", "error": f"LLM generate: {e}"}

    if not ttl2_path.exists():
        try:
            run_oscin([
                "extract", str(gen_dir),
                "--framework", tgt_fw,
                "--system-name", system_name,
                "--namespace", ns,
                "--output", str(ttl2_path),
                "--no-report",
            ])
        except Exception as e:
            return {"status": "error", "error": f"Re-extract: {e}"}

    g1 = load_graph(ttl1_path)
    g2 = load_graph(ttl2_path)

    if g1 and g2:
        pw = compute_pairwise(g1, g2)
        fuzzy_result = ttl_fuzzy_match.compute(g1, g2)
        syn_result = syntax_validity.compute(gen_dir)
        ast_result = ast_diff.compute(source_dir, gen_dir)

        return {
            "status": "ok",
            "triple_f1": pw.triple_f1,
            "aligned_f1": pw.aligned_triple_f1,
            "property_f1": pw.property_f1,
            "individual_f1": pw.individual_f1,
            "literal_overlap": pw.literal_overlap,
            "fuzzy_avg": fuzzy_result.get("avg_score"),
            "ast_f1": (ast_result.get("overall") or {}).get("f1") if isinstance(ast_result, dict) and "error" not in ast_result else None,
            "syntax_rate": syn_result.get("syntax_rate"),
            "import_rate": syn_result.get("import_rate"),
        }
    else:
        return {"status": "error", "error": "graph parse failed"}


# ===================================================================
# Reporting helpers
# ===================================================================

METRIC_KEYS = [
    "triple_f1", "aligned_f1", "property_f1", "individual_f1",
    "literal_overlap", "fuzzy_avg", "ast_f1", "syntax_rate", "import_rate",
]


def _log_row(row: dict):
    """Log a compact summary line for one example."""
    parts = []
    for approach in ("deterministic", "hybrid", "llm"):
        m = row.get(approach, {})
        if m.get("status") == "ok":
            tf1 = m.get("triple_f1")
            af1 = m.get("ast_f1")
            syn = m.get("syntax_rate")
            parts.append(f"{approach}: TF1={tf1:.3f}" if tf1 else f"{approach}: TF1=N/A")
            if af1 is not None:
                parts[-1] += f" AF1={af1:.3f}"
            if syn is not None:
                parts[-1] += f" Syn={syn:.2f}"
        else:
            parts.append(f"{approach}: ERR")
    log.info("    " + " | ".join(parts))


def _write_results(results: list[dict], out_prefix: Path):
    """Write results as JSON and a summary CSV."""
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    # JSON
    (out_prefix.with_suffix(".json")).write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )

    # Flattened CSV-friendly rows
    csv_rows = []
    for row in results:
        flat = {}
        if "framework" in row:
            flat["framework"] = row["framework"]
        if "direction" in row:
            flat["direction"] = row["direction"]
        flat["example"] = row["example"]
        for approach in ("deterministic", "hybrid", "llm"):
            m = row.get(approach, {})
            for key in METRIC_KEYS:
                flat[f"{approach}_{key}"] = m.get(key)
        csv_rows.append(flat)

    (out_prefix.with_suffix(".csv.json")).write_text(
        json.dumps(csv_rows, indent=2, default=str), encoding="utf-8"
    )

    # Aggregate summary
    summary = _compute_aggregates(results)
    (out_prefix.parent / (out_prefix.name + "_summary.json")).write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    # Markdown summary
    md = _render_summary_markdown(results, summary)
    (out_prefix.parent / (out_prefix.name + "_summary.md")).write_text(
        md, encoding="utf-8"
    )

    log.info(f"  Wrote results to {out_prefix.parent}")


def _compute_aggregates(results: list[dict]) -> dict:
    """Compute per-framework aggregates for each approach and metric."""
    groups: dict[str, list[dict]] = {}
    for row in results:
        key = row.get("framework") or row.get("direction", "all")
        groups.setdefault(key, []).append(row)

    aggregates = {}
    for group_name, rows in sorted(groups.items()):
        agg = {"n": len(rows)}
        for approach in ("deterministic", "hybrid", "llm"):
            for key in METRIC_KEYS:
                vals = [
                    r.get(approach, {}).get(key)
                    for r in rows
                    if r.get(approach, {}).get("status") == "ok" and r.get(approach, {}).get(key) is not None
                ]
                if vals:
                    agg[f"{approach}_{key}_mean"] = round(statistics.mean(vals), 3)
                    if len(vals) > 1:
                        agg[f"{approach}_{key}_std"] = round(statistics.stdev(vals), 3)
                    else:
                        agg[f"{approach}_{key}_std"] = 0.0
                else:
                    agg[f"{approach}_{key}_mean"] = None
                    agg[f"{approach}_{key}_std"] = None
        aggregates[group_name] = agg

    return aggregates


def _render_summary_markdown(results: list[dict], aggregates: dict) -> str:
    """Render a markdown summary table."""
    lines = ["# Generation Approach Comparison\n"]

    for approach in ("deterministic", "hybrid", "llm"):
        label = {
            "deterministic": "Deterministic (AST)",
            "hybrid": "Hybrid (AST + LLM Fixup)",
            "llm": "Pure LLM",
        }[approach]
        lines.append(f"\n## {label}\n")
        lines.append("| Framework | Example | Triple F1 | Aligned F1 | AST F1 | Syntax |")
        lines.append("|-----------|---------|-----------|-------------|--------|--------|")
        for row in results:
            m = row.get(approach, {})
            fw = row.get("framework") or row.get("direction", "")
            ex = row.get("example", "")
            if m.get("status") == "ok":
                tf = m.get("triple_f1")
                af = m.get("aligned_f1")
                astf = m.get("ast_f1")
                syn = m.get("syntax_rate")
                lines.append(
                    f"| {fw} | {ex} | "
                    f"{tf:.3f} | {af:.3f} | {astf:.3f if astf else '–'} | "
                    f"{syn:.2f if syn else '–'} |"
                )
            else:
                lines.append(f"| {fw} | {ex} | ERR | ERR | ERR | ERR |")

    # Aggregate table
    lines.append("\n## Aggregate (mean ± std)\n")
    lines.append(
        "| Group | N | "
        "Det TF1 | Hyb TF1 | LLM TF1 | "
        "Det AF1 | Hyb AF1 | LLM AF1 | "
        "Det Syn | Hyb Syn | LLM Syn |"
    )
    lines.append(
        "|-------|---|"
        "---------|---------|---------|"
        "---------|---------|---------|"
        "---------|---------|---------|"
    )
    for group_name, agg in sorted(aggregates.items()):
        n = agg["n"]
        cols = []
        for metric in ("triple_f1", "aligned_f1", "syntax_rate"):
            for approach in ("deterministic", "hybrid", "llm"):
                mean = agg.get(f"{approach}_{metric}_mean")
                std = agg.get(f"{approach}_{metric}_std")
                if mean is not None:
                    cols.append(f"{mean:.3f}±{std:.3f}" if std else f"{mean:.3f}")
                else:
                    cols.append("–")
        lines.append(f"| {group_name} | {n} | " + " | ".join(cols) + " |")

    return "\n".join(lines)


# ===================================================================
# MAIN
# ===================================================================

def main():
    import argparse
    ap = argparse.ArgumentParser(description="3-way generation comparison: deterministic vs hybrid vs pure LLM")
    ap.add_argument("--phase", type=int, nargs="*", default=[1, 2],
                    help="Which phases to run. 1=same-fw, 2=cross-fw. Default: both")
    ap.add_argument("--provider", default="openai", help="LLM provider (openai or anthropic)")
    ap.add_argument("--model", default=None, help="LLM model (default: gpt-4o for openai)")
    args = ap.parse_args()

    global LLM_PROVIDER, LLM_MODEL
    LLM_PROVIDER = args.provider
    if args.model:
        LLM_MODEL = args.model

    phases = args.phase

    if 1 in phases:
        run_same_fw_comparison()
    if 2 in phases:
        run_cross_fw_comparison()

    log.info("\n\nDONE. All results in: %s", OUT_ROOT)


if __name__ == "__main__":
    main()