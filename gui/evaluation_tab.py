"""
gui.evaluation_tab
==================
Full evaluation pipeline tab for the OSCIN GUI.

Supports:
- Deterministic (AST) same-framework roundtrip
- Deterministic (AST) cross-framework roundtrip
- LLM-based same-framework roundtrip
- LLM-based cross-framework roundtrip

Results are displayed as sortable tables with per-example metrics.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

import streamlit as st
from rdflib import Graph

from evaluation.pipelines._common import (
    PROJECT_ROOT,
    StepFailed,
    default_namespace,
    default_system_name,
    resolve_source_dir,
    run_oscin,
    run_step,
)
from evaluation.pipelines.roundtrip import run_roundtrip
from evaluation.metrics import ttl_pairwise, ttl_fuzzy_match, ast_diff
from evaluation.metrics import extraction_coverage
from oscin.evaluator import compute_pairwise, compute_intrinsic
from gui.components import FRAMEWORKS, capture_logs

log = logging.getLogger("oscin.eval.gui")

GUI_OUT_ROOT = PROJECT_ROOT / "output" / "gui" / "evaluation"
EVAL_FULL_ROOT = PROJECT_ROOT / "output" / "eval_full"

EXAMPLES_ROOT = PROJECT_ROOT / "examples"

# All examples by framework
CREWAI_EXAMPLES = sorted(
    [p.name for p in (EXAMPLES_ROOT / "crewai").iterdir() if p.is_dir()]
) if (EXAMPLES_ROOT / "crewai").is_dir() else []

LANGGRAPH_EXAMPLES = sorted(
    [p.name for p in (EXAMPLES_ROOT / "langgraph").iterdir() if p.is_dir()]
) if (EXAMPLES_ROOT / "langgraph").is_dir() else []

AUTOGEN_EXAMPLES = sorted(
    [p.name for p in (EXAMPLES_ROOT / "autogen").iterdir() if p.is_dir()]
) if (EXAMPLES_ROOT / "autogen").is_dir() else []

ALL_EXAMPLES = (
    [("crewai", ex) for ex in CREWAI_EXAMPLES]
    + [("langgraph", ex) for ex in LANGGRAPH_EXAMPLES]
    + [("autogen", ex) for ex in AUTOGEN_EXAMPLES]
)


def _resolve_example_root(fw: str, name: str) -> Path:
    return EXAMPLES_ROOT / fw / name


def _load_graph(path: Path) -> Graph | None:
    if not path.exists():
        return None
    g = Graph()
    try:
        g.parse(str(path), format="turtle")
        return g
    except Exception:
        return None


# ===================================================================
# Deterministic (AST) pipeline runners
# ===================================================================

def _run_ast_same_fw(
    frameworks: list[str],
    progress_bar,
    status_text,
) -> list[dict]:
    """Run AST same-framework roundtrip for selected frameworks."""
    examples = [(fw, ex) for fw, ex in ALL_EXAMPLES if fw in frameworks]
    results = []
    total = len(examples)

    for i, (fw, ex) in enumerate(examples):
        progress_bar.progress((i) / total, text=f"[{i+1}/{total}] {fw}/{ex}")
        status_text.text(f"Running: {fw}/{ex} (same-fw roundtrip)")

        example_root = _resolve_example_root(fw, ex)
        out_root = GUI_OUT_ROOT / "ast_same_fw"

        try:
            report = run_roundtrip(
                example_root, fw,
                skip_execution=True,
                out_root=out_root,
            )
            pw = report.get("metrics", {}).get("ttl_pairwise", {})
            fuzzy = report.get("metrics", {}).get("ttl_fuzzy_match", {})
            ast = report.get("metrics", {}).get("ast_diff", {})

            results.append({
                "Framework": fw,
                "Example": ex,
                "Triple F1": pw.get("triple_f1"),
                "Aligned F1": pw.get("aligned_triple_f1"),
                "Property F1": pw.get("property_f1"),
                "Individual F1": pw.get("individual_f1"),
                "Literal Overlap": pw.get("literal_overlap"),
                "Fuzzy Avg": fuzzy.get("avg_score"),
                "AST F1": (ast.get("overall") or {}).get("f1") if isinstance(ast, dict) else None,
                "Status": "✓",
            })
        except Exception as e:
            results.append({
                "Framework": fw,
                "Example": ex,
                "Triple F1": None,
                "Aligned F1": None,
                "Property F1": None,
                "Individual F1": None,
                "Literal Overlap": None,
                "Fuzzy Avg": None,
                "AST F1": None,
                "Status": f"✗ {e}",
            })

    progress_bar.progress(1.0, text="Done")
    return results


def _run_ast_cross_fw(
    directions: list[tuple[str, str]],
    progress_bar,
    status_text,
) -> list[dict]:
    """Run AST cross-framework roundtrip for selected directions."""
    results = []

    # Build list of (src_fw, tgt_fw, example_name)
    jobs = []
    for src_fw, tgt_fw in directions:
        src_examples = {
            "crewai": CREWAI_EXAMPLES,
            "langgraph": LANGGRAPH_EXAMPLES,
            "autogen": AUTOGEN_EXAMPLES,
        }.get(src_fw, [])
        for ex in src_examples:
            jobs.append((src_fw, tgt_fw, ex))

    total = len(jobs)
    for i, (src_fw, tgt_fw, ex) in enumerate(jobs):
        progress_bar.progress(i / total, text=f"[{i+1}/{total}] {src_fw}→{tgt_fw}/{ex}")
        status_text.text(f"Running: {src_fw}→{tgt_fw}/{ex}")

        example_root = _resolve_example_root(src_fw, ex)
        out_root = GUI_OUT_ROOT / "ast_cross_fw" / f"{src_fw}_to_{tgt_fw}"

        try:
            report = run_roundtrip(
                example_root, src_fw,
                target_framework=tgt_fw,
                skip_execution=True,
                out_root=out_root,
            )
            pw = report.get("metrics", {}).get("ttl_pairwise", {})
            fuzzy = report.get("metrics", {}).get("ttl_fuzzy_match", {})

            results.append({
                "Direction": f"{src_fw}→{tgt_fw}",
                "Example": ex,
                "Triple F1": pw.get("triple_f1"),
                "Aligned F1": pw.get("aligned_triple_f1"),
                "Property F1": pw.get("property_f1"),
                "Individual F1": pw.get("individual_f1"),
                "Literal Overlap": pw.get("literal_overlap"),
                "Fuzzy Avg": fuzzy.get("avg_score"),
                "Status": "✓",
            })
        except Exception as e:
            results.append({
                "Direction": f"{src_fw}→{tgt_fw}",
                "Example": ex,
                "Triple F1": None,
                "Aligned F1": None,
                "Property F1": None,
                "Individual F1": None,
                "Literal Overlap": None,
                "Fuzzy Avg": None,
                "Status": f"✗ {e}",
            })

    progress_bar.progress(1.0, text="Done")
    return results


# ===================================================================
# LLM pipeline runners
# ===================================================================

def _run_llm_same_fw(
    frameworks: list[str],
    provider: str,
    model: str,
    progress_bar,
    status_text,
) -> list[dict]:
    """Run LLM same-framework roundtrip."""
    from oscin.llm_extractor import run_llm_extraction
    from oscin.llm_generator import run_llm_generation

    examples = [(fw, ex) for fw, ex in ALL_EXAMPLES if fw in frameworks]
    results = []
    total = len(examples)

    for i, (fw, ex) in enumerate(examples):
        progress_bar.progress(i / total, text=f"[{i+1}/{total}] {fw}/{ex}")
        status_text.text(f"LLM roundtrip: {fw}/{ex}")

        example_root = _resolve_example_root(fw, ex)
        source_dir = resolve_source_dir(example_root)
        work = GUI_OUT_ROOT / "llm_same_fw" / fw / ex
        work.mkdir(parents=True, exist_ok=True)

        ns = default_namespace(ex)
        system_name = default_system_name(ex)

        ttl1_path = work / "ttl1_llm.ttl"
        gen_dir = work / "generated"
        ttl2_path = work / "ttl2.ttl"

        try:
            # Step 1: LLM extraction → TTL₁
            if not ttl1_path.exists():
                run_llm_extraction(
                    source_dir=source_dir,
                    output_path=ttl1_path,
                    instance_namespace=ns,
                    provider=provider,
                    model=model,
                )

            # Step 2: LLM generation → source′
            if not gen_dir.exists() or not list(gen_dir.glob("**/*.py")):
                run_llm_generation(
                    ttl_file=ttl1_path,
                    output_dir=gen_dir,
                    target_framework=fw,
                    provider=provider,
                    model=model,
                )

            # Step 3: AST re-extraction → TTL₂
            if not ttl2_path.exists():
                run_oscin([
                    "extract", str(gen_dir),
                    "--framework", fw,
                    "--system-name", system_name,
                    "--namespace", ns,
                    "--output", str(ttl2_path),
                    "--no-report",
                ])

            # Step 4: Compare
            g1 = _load_graph(ttl1_path)
            g2 = _load_graph(ttl2_path)

            if g1 and g2:
                pw = compute_pairwise(g1, g2)
                results.append({
                    "Framework": fw,
                    "Example": ex,
                    "Triple F1": round(pw.triple_f1, 3),
                    "Aligned F1": round(pw.aligned_triple_f1, 3),
                    "Property F1": round(pw.property_f1, 3),
                    "Individual F1": round(pw.individual_f1, 3),
                    "Literal Overlap": round(pw.literal_overlap, 3),
                    "Status": "✓",
                })
            else:
                results.append({
                    "Framework": fw,
                    "Example": ex,
                    "Triple F1": None,
                    "Aligned F1": None,
                    "Property F1": None,
                    "Individual F1": None,
                    "Literal Overlap": None,
                    "Status": "✗ graph parse failed",
                })

        except Exception as e:
            results.append({
                "Framework": fw,
                "Example": ex,
                "Triple F1": None,
                "Aligned F1": None,
                "Property F1": None,
                "Individual F1": None,
                "Literal Overlap": None,
                "Status": f"✗ {e}",
            })

    progress_bar.progress(1.0, text="Done")
    return results


def _run_llm_cross_fw(
    directions: list[tuple[str, str]],
    provider: str,
    model: str,
    progress_bar,
    status_text,
) -> list[dict]:
    """Run LLM cross-framework roundtrip."""
    from oscin.llm_extractor import run_llm_extraction
    from oscin.llm_generator import run_llm_generation

    jobs = []
    for src_fw, tgt_fw in directions:
        src_examples = {
            "crewai": CREWAI_EXAMPLES,
            "langgraph": LANGGRAPH_EXAMPLES,
            "autogen": AUTOGEN_EXAMPLES,
        }.get(src_fw, [])
        for ex in src_examples:
            jobs.append((src_fw, tgt_fw, ex))

    results = []
    total = len(jobs)

    for i, (src_fw, tgt_fw, ex) in enumerate(jobs):
        progress_bar.progress(i / total, text=f"[{i+1}/{total}] {src_fw}→{tgt_fw}/{ex}")
        status_text.text(f"LLM cross-fw: {src_fw}→{tgt_fw}/{ex}")

        example_root = _resolve_example_root(src_fw, ex)
        source_dir = resolve_source_dir(example_root)
        work = GUI_OUT_ROOT / "llm_cross_fw" / f"{src_fw}_to_{tgt_fw}" / ex
        work.mkdir(parents=True, exist_ok=True)

        ns = default_namespace(ex)
        system_name = default_system_name(ex)

        ttl1_path = work / "ttl1_llm.ttl"
        gen_dir = work / "generated"
        ttl2_path = work / "ttl2.ttl"

        try:
            # Step 1: LLM extraction
            if not ttl1_path.exists():
                run_llm_extraction(
                    source_dir=source_dir,
                    output_path=ttl1_path,
                    instance_namespace=ns,
                    provider=provider,
                    model=model,
                )

            # Step 2: LLM generation to target framework
            if not gen_dir.exists() or not list(gen_dir.glob("**/*.py")):
                run_llm_generation(
                    ttl_file=ttl1_path,
                    output_dir=gen_dir,
                    target_framework=tgt_fw,
                    provider=provider,
                    model=model,
                )

            # Step 3: AST re-extraction
            if not ttl2_path.exists():
                run_oscin([
                    "extract", str(gen_dir),
                    "--framework", tgt_fw,
                    "--system-name", system_name,
                    "--namespace", ns,
                    "--output", str(ttl2_path),
                    "--no-report",
                ])

            # Step 4: Compare
            g1 = _load_graph(ttl1_path)
            g2 = _load_graph(ttl2_path)

            if g1 and g2:
                pw = compute_pairwise(g1, g2)
                results.append({
                    "Direction": f"{src_fw}→{tgt_fw}",
                    "Example": ex,
                    "Triple F1": round(pw.triple_f1, 3),
                    "Aligned F1": round(pw.aligned_triple_f1, 3),
                    "Property F1": round(pw.property_f1, 3),
                    "Individual F1": round(pw.individual_f1, 3),
                    "Literal Overlap": round(pw.literal_overlap, 3),
                    "Status": "✓",
                })
            else:
                results.append({
                    "Direction": f"{src_fw}→{tgt_fw}",
                    "Example": ex,
                    "Triple F1": None,
                    "Aligned F1": None,
                    "Property F1": None,
                    "Individual F1": None,
                    "Literal Overlap": None,
                    "Status": "✗ graph parse failed",
                })

        except Exception as e:
            results.append({
                "Direction": f"{src_fw}→{tgt_fw}",
                "Example": ex,
                "Triple F1": None,
                "Aligned F1": None,
                "Property F1": None,
                "Individual F1": None,
                "Literal Overlap": None,
                "Status": f"✗ {e}",
            })

    progress_bar.progress(1.0, text="Done")
    return results


# ===================================================================
# Extraction coverage runner
# ===================================================================

def _run_extraction_coverage(
    frameworks: list[str],
    progress_bar,
    status_text,
    ttl_source: str = "fresh",  # "fresh" = extract now, "cached" = use eval_full
) -> list[dict]:
    """Run extraction coverage for selected frameworks.

    Measures how well the extraction captures source code elements.
    """
    examples = [(fw, ex) for fw, ex in ALL_EXAMPLES if fw in frameworks]
    results = []
    total = len(examples)

    for i, (fw, ex) in enumerate(examples):
        progress_bar.progress(i / total, text=f"[{i+1}/{total}] {fw}/{ex}")
        status_text.text(f"Extraction coverage: {fw}/{ex}")

        example_root = _resolve_example_root(fw, ex)
        source_dir = resolve_source_dir(example_root)

        # Find or create the extracted TTL
        ttl_path = None
        if ttl_source == "cached":
            # Try loading from eval_full
            cached = EVAL_FULL_ROOT / "ast_same_fw" / fw / ex / "ttl1.ttl"
            if cached.exists():
                ttl_path = cached

        if ttl_path is None:
            # Extract fresh
            work = GUI_OUT_ROOT / "extraction_coverage" / fw / ex
            work.mkdir(parents=True, exist_ok=True)
            ttl_path = work / "extracted.ttl"
            if not ttl_path.exists():
                try:
                    ns = default_namespace(ex)
                    system_name = default_system_name(ex)
                    run_oscin([
                        "extract", str(source_dir),
                        "--framework", fw,
                        "--system-name", system_name,
                        "--namespace", ns,
                        "--output", str(ttl_path),
                        "--no-report",
                    ])
                except Exception as e:
                    results.append({
                        "Framework": fw,
                        "Example": ex,
                        "Overall": None,
                        "Element F1": None,
                        "Rel. Recall": None,
                        "Content Recall": None,
                        "Status": f"✗ extract failed: {e}",
                    })
                    continue

        # Run coverage metric
        try:
            cov = extraction_coverage.compute(str(source_dir), str(ttl_path), fw)
            if "error" in cov:
                results.append({
                    "Framework": fw,
                    "Example": ex,
                    "Overall": None,
                    "Element F1": None,
                    "Rel. Recall": None,
                    "Content Recall": None,
                    "Status": f"✗ {cov['error']}",
                })
            else:
                # Build per-element detail columns
                elem = cov.get("element_coverage", {})
                results.append({
                    "Framework": fw,
                    "Example": ex,
                    "Overall": cov["overall_score"],
                    "Element F1": cov["element_macro_f1"],
                    "Rel. Recall": cov["relationship_avg_recall"],
                    "Content Recall": cov["content_recall"],
                    "Agents F1": elem.get("agents", {}).get("f1"),
                    "Tasks F1": elem.get("tasks", {}).get("f1"),
                    "Tools F1": elem.get("tools", {}).get("f1"),
                    "Teams F1": elem.get("teams", {}).get("f1"),
                    "Steps F1": elem.get("flow_steps", {}).get("f1"),
                    "Status": "✓",
                })
        except Exception as e:
            results.append({
                "Framework": fw,
                "Example": ex,
                "Overall": None,
                "Element F1": None,
                "Rel. Recall": None,
                "Content Recall": None,
                "Status": f"✗ {e}",
            })

    progress_bar.progress(1.0, text="Done")
    return results


# ===================================================================
# Aggregation helpers
# ===================================================================

def _compute_aggregates(results: list[dict], group_col: str = "Framework") -> list[dict]:
    """Compute mean metrics grouped by a column."""
    from collections import defaultdict
    import statistics

    if not results:
        return []

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        groups[row[group_col]].append(row)

    # Auto-detect numeric metric columns (exclude Status, Framework, Example, etc.)
    skip_cols = {group_col, "Status", "Example", "N", "Direction"}
    first_row = results[0]
    metric_cols = [
        k for k, v in first_row.items()
        if k not in skip_cols and isinstance(v, (int, float, type(None)))
    ]

    agg_rows = []
    for group_name, rows in sorted(groups.items()):
        agg = {group_col: group_name, "N": len(rows)}
        for col in metric_cols:
            vals = [r[col] for r in rows if r.get(col) is not None]
            agg[f"{col} (mean)"] = round(statistics.mean(vals), 3) if vals else None
        agg_rows.append(agg)

    # Overall row
    all_agg = {group_col: "**Overall**", "N": len(results)}
    for col in metric_cols:
        vals = [r[col] for r in results if r.get(col) is not None]
        all_agg[f"{col} (mean)"] = round(statistics.mean(vals), 3) if vals else None
    agg_rows.append(all_agg)

    return agg_rows


# ===================================================================
# Load prior results from output/eval_full/
# ===================================================================


def _load_prior_ast_same_fw() -> list[dict] | None:
    """Load prior AST same-fw results from output/eval_full/.

    Always recomputes pairwise metrics from TTL files to use the latest
    evaluator (with blank-node fix). Falls back to report.json for
    AST F1 and Fuzzy Avg which don't depend on the evaluator fix.
    """
    base = EVAL_FULL_ROOT / "ast_same_fw"
    if not base.is_dir():
        return None

    results = []
    for fw in ["crewai", "langgraph", "autogen"]:
        fw_dir = base / fw
        if not fw_dir.is_dir():
            continue
        for ex_dir in sorted(fw_dir.iterdir()):
            if not ex_dir.is_dir():
                continue
            t1 = ex_dir / "ttl1.ttl"
            t2 = ex_dir / "ttl2.ttl"
            if not (t1.exists() and t2.exists()):
                continue

            # Always recompute pairwise from TTL (ensures updated evaluator)
            try:
                g1 = Graph(); g1.parse(str(t1), format="turtle")
                g2 = Graph(); g2.parse(str(t2), format="turtle")
                pw = compute_pairwise(g1, g2)

                # Try to get AST F1 and Fuzzy from report.json
                ast_f1 = None
                fuzzy_avg = None
                report_file = ex_dir / "report.json"
                if report_file.exists():
                    report = json.loads(report_file.read_text())
                    ast_data = report.get("metrics", {}).get("ast_diff", {})
                    fuzzy_data = report.get("metrics", {}).get("ttl_fuzzy_match", {})
                    ast_f1 = (ast_data.get("overall") or {}).get("f1") if isinstance(ast_data, dict) else None
                    fuzzy_avg = fuzzy_data.get("avg_score") if isinstance(fuzzy_data, dict) else None

                results.append({
                    "Framework": fw,
                    "Example": ex_dir.name,
                    "Triple F1": round(pw.triple_f1, 3),
                    "Aligned F1": round(pw.aligned_triple_f1, 3),
                    "Property F1": round(pw.property_f1, 3),
                    "Individual F1": round(pw.individual_f1, 3),
                    "Literal Overlap": round(pw.literal_overlap, 3),
                    "Fuzzy Avg": fuzzy_avg,
                    "AST F1": ast_f1,
                    "Status": "✓ (recomputed)",
                })
            except Exception:
                pass

    return results if results else None


def _load_prior_ast_cross_fw() -> list[dict] | None:
    """Load prior AST cross-fw results from output/eval_full/.

    Recomputes metrics from TTL files with the latest evaluator.
    """
    base = EVAL_FULL_ROOT / "ast_cross_fw"
    if not base.is_dir():
        return None

    results = []
    for dir_entry in sorted(base.iterdir()):
        if not dir_entry.is_dir() or dir_entry.name.endswith(".json"):
            continue
        # Directory name is like "crewai_to_langgraph"
        parts = dir_entry.name.split("_to_")
        if len(parts) != 2:
            continue
        src_fw, tgt_fw = parts

        # Walk subdirectories to find ttl1.ttl/ttl2.ttl pairs
        # Structure: dir_entry/<src_fw>/<example>/ (from run_roundtrip)
        def _collect_from_dir(search_dir: Path, depth: int = 0):
            if depth > 2:
                return
            for sub in sorted(search_dir.iterdir()):
                if not sub.is_dir():
                    continue
                t1 = sub / "ttl1.ttl"
                t2 = sub / "ttl2.ttl"
                if t1.exists() and t2.exists():
                    try:
                        g1 = Graph(); g1.parse(str(t1), format="turtle")
                        g2 = Graph(); g2.parse(str(t2), format="turtle")
                        pw = compute_pairwise(g1, g2)

                        fuzzy_avg = None
                        report_file = sub / "report.json"
                        if report_file.exists():
                            report = json.loads(report_file.read_text())
                            fuzzy_data = report.get("metrics", {}).get("ttl_fuzzy_match", {})
                            fuzzy_avg = fuzzy_data.get("avg_score") if isinstance(fuzzy_data, dict) else None

                        results.append({
                            "Direction": f"{src_fw}→{tgt_fw}",
                            "Example": sub.name,
                            "Triple F1": round(pw.triple_f1, 3),
                            "Aligned F1": round(pw.aligned_triple_f1, 3),
                            "Property F1": round(pw.property_f1, 3),
                            "Individual F1": round(pw.individual_f1, 3),
                            "Literal Overlap": round(pw.literal_overlap, 3),
                            "Fuzzy Avg": fuzzy_avg,
                            "Status": "✓ (recomputed)",
                        })
                    except Exception:
                        pass
                else:
                    # Recurse one level deeper
                    _collect_from_dir(sub, depth + 1)

        _collect_from_dir(dir_entry)

    return results if results else None


# ===================================================================
# Main tab render function
# ===================================================================

def render_evaluation_tab():
    """Render the full Evaluate tab content."""
    st.header("Full Evaluation Pipeline")
    st.caption(
        "Run the evaluation pipeline across all examples. "
        "Choose between the deterministic (AST) pipeline or the LLM-based pipeline. "
        "Results are displayed as tables with per-example and aggregate metrics."
    )

    # Mode selection
    eval_mode = st.radio(
        "Pipeline mode",
        options=["Deterministic (AST)", "LLM-based"],
        key="eval_mode",
        horizontal=True,
    )

    # --- Configuration ---
    col_config, col_info = st.columns([1, 2], gap="large")

    with col_config:
        st.subheader("Configuration")

        # Evaluation type
        eval_type = st.radio(
            "Evaluation type",
            options=["Same-framework roundtrip", "Cross-framework roundtrip", "Extraction coverage", "Both"],
            key="eval_type",
            horizontal=False,
        )

        # Framework selection
        st.markdown("**Frameworks to evaluate:**")
        fw_crewai = st.checkbox("CrewAI", value=True, key="eval_fw_crewai")
        fw_langgraph = st.checkbox("LangGraph", value=True, key="eval_fw_langgraph")
        fw_autogen = st.checkbox("AutoGen", value=True, key="eval_fw_autogen")

        selected_fws = []
        if fw_crewai:
            selected_fws.append("crewai")
        if fw_langgraph:
            selected_fws.append("langgraph")
        if fw_autogen:
            selected_fws.append("autogen")

        # Cross-framework directions
        cross_directions: list[tuple[str, str]] = []
        if eval_type in ("Cross-framework roundtrip", "Both"):
            st.markdown("**Cross-framework directions:**")
            available_dirs = [
                ("crewai", "langgraph"),
                ("crewai", "autogen"),
                ("langgraph", "crewai"),
                ("langgraph", "autogen"),
                ("autogen", "crewai"),
                ("autogen", "langgraph"),
            ]
            for src, tgt in available_dirs:
                if src in selected_fws:
                    checked = st.checkbox(
                        f"{src} → {tgt}",
                        value=True,
                        key=f"eval_dir_{src}_{tgt}",
                    )
                    if checked:
                        cross_directions.append((src, tgt))

        # LLM config
        if eval_mode == "LLM-based":
            st.divider()
            st.markdown("**LLM Configuration**")
            llm_provider = st.selectbox(
                "Provider",
                options=["openai", "anthropic"],
                key="eval_llm_provider",
            )
            default_models = {
                "openai": "gpt-4o",
                "anthropic": "claude-sonnet-4-20250514",
            }
            llm_model = st.text_input(
                "Model",
                value=default_models.get(llm_provider, "gpt-4o"),
                key="eval_llm_model",
            )
            st.caption(
                "LLM runs are cached — existing outputs will be reused. "
                "Delete the output directory to force a re-run."
            )

        # Use cached results
        use_cache = st.checkbox(
            "Use cached results (skip if output exists)",
            value=True,
            key="eval_use_cache",
            help="If checked, existing results from prior runs will be reused.",
        )

    with col_info:
        st.subheader("Pipeline Overview")
        if eval_mode == "Deterministic (AST)":
            st.markdown("""
**Deterministic (AST) Pipeline:**
```
source → AST extract → TTL₁ → template generate → source′ → AST extract → TTL₂
```

- Uses rule-based Python AST parsing for extraction
- Uses Jinja2 templates for code generation
- Fully deterministic — same input always produces same output
- No API calls required
            """)
        else:
            st.markdown("""
**LLM-based Pipeline:**
```
source → LLM extract → TTL₁ → LLM generate → source′ → AST extract → TTL₂
```

- Uses LLM (GPT-4o / Claude) for extraction and generation
- Re-extraction in step 3 uses AST (deterministic) for fair comparison
- Requires API keys in `.env`
- Non-deterministic — results vary between runs
            """)

        n_same = len([(fw, ex) for fw, ex in ALL_EXAMPLES if fw in selected_fws])
        n_cross = sum(
            len({
                "crewai": CREWAI_EXAMPLES,
                "langgraph": LANGGRAPH_EXAMPLES,
                "autogen": AUTOGEN_EXAMPLES,
            }.get(src, []))
            for src, _ in cross_directions
        )

        if eval_type == "Extraction coverage":
            st.markdown(f"""
**Scope:**
- Examples to evaluate: **{n_same}**
- Measures how completely the extraction captures source elements into TTL
            """)
        else:
            st.markdown(f"""
**Scope:**
- Same-fw examples: **{n_same}** {'(selected)' if eval_type not in ('Cross-framework roundtrip',) else '(skipped)'}
- Cross-fw examples: **{n_cross}** {'(selected)' if eval_type not in ('Same-framework roundtrip', 'Extraction coverage') else '(skipped)'}
            """)

    # --- Run / Load buttons ---
    st.divider()
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        run_eval = st.button(
            "Run Evaluation",
            type="primary",
            disabled=len(selected_fws) == 0,
            key="eval_run",
            use_container_width=True,
        )
    with btn_col2:
        has_prior = EVAL_FULL_ROOT.is_dir()
        load_prior = st.button(
            "Load Prior Results" + (" (from output/eval_full/)" if has_prior else ""),
            disabled=not has_prior,
            key="eval_load_prior",
            use_container_width=True,
            help="Re-compute metrics from cached TTL files in output/eval_full/. "
                 "Uses the updated evaluator (blank-node fix applied).",
        )

    if load_prior:
        with st.spinner("Loading and recomputing from prior results..."):
            same = _load_prior_ast_same_fw()
            cross = _load_prior_ast_cross_fw()
            if same:
                st.session_state["eval_same_fw_results"] = same
            if cross:
                st.session_state["eval_cross_fw_results"] = cross
            st.session_state["eval_mode_used"] = "Deterministic (AST) — loaded from cache"
            st.session_state["eval_elapsed"] = 0
            st.rerun()

    if run_eval:
        progress_bar = st.progress(0, text="Starting...")
        status_text = st.empty()
        start_time = time.time()

        with capture_logs() as cap:
            try:
                if eval_type == "Extraction coverage":
                    # Extraction coverage (works for both AST and LLM modes)
                    status_text.text("Phase: Extraction coverage analysis")
                    ttl_src = "cached" if EVAL_FULL_ROOT.is_dir() else "fresh"
                    cov_results = _run_extraction_coverage(
                        selected_fws, progress_bar, status_text,
                        ttl_source=ttl_src,
                    )
                    st.session_state["eval_coverage_results"] = cov_results

                elif eval_mode == "Deterministic (AST)":
                    # Same-fw
                    if eval_type in ("Same-framework roundtrip", "Both"):
                        status_text.text("Phase: AST same-framework roundtrip")
                        same_results = _run_ast_same_fw(
                            selected_fws, progress_bar, status_text
                        )
                        st.session_state["eval_same_fw_results"] = same_results

                    # Cross-fw
                    if eval_type in ("Cross-framework roundtrip", "Both"):
                        status_text.text("Phase: AST cross-framework roundtrip")
                        cross_results = _run_ast_cross_fw(
                            cross_directions, progress_bar, status_text
                        )
                        st.session_state["eval_cross_fw_results"] = cross_results

                else:  # LLM-based
                    provider = st.session_state.get("eval_llm_provider", "openai")
                    model = st.session_state.get("eval_llm_model", "gpt-4o")

                    if eval_type in ("Same-framework roundtrip", "Both"):
                        status_text.text("Phase: LLM same-framework roundtrip")
                        same_results = _run_llm_same_fw(
                            selected_fws, provider, model,
                            progress_bar, status_text,
                        )
                        st.session_state["eval_same_fw_results"] = same_results

                    if eval_type in ("Cross-framework roundtrip", "Both"):
                        status_text.text("Phase: LLM cross-framework roundtrip")
                        cross_results = _run_llm_cross_fw(
                            cross_directions, provider, model,
                            progress_bar, status_text,
                        )
                        st.session_state["eval_cross_fw_results"] = cross_results

            except Exception as e:
                st.error(f"Evaluation failed: {type(e).__name__}: {e}")
                traceback.print_exc()

        elapsed = time.time() - start_time
        status_text.text(f"Completed in {elapsed:.1f}s")
        st.session_state["eval_logs"] = list(cap.handler.records)
        st.session_state["eval_mode_used"] = eval_mode
        st.session_state["eval_elapsed"] = elapsed

    # --- Display results ---
    _render_results()


def _render_results():
    """Render stored evaluation results."""
    same_results = st.session_state.get("eval_same_fw_results")
    cross_results = st.session_state.get("eval_cross_fw_results")
    coverage_results = st.session_state.get("eval_coverage_results")

    if not same_results and not cross_results and not coverage_results:
        return

    st.divider()
    mode_used = st.session_state.get("eval_mode_used", "")
    elapsed = st.session_state.get("eval_elapsed", 0)
    st.success(f"Evaluation complete ({mode_used}, {elapsed:.1f}s)")

    # --- Same-framework results ---
    if same_results:
        st.subheader("Same-Framework Roundtrip Results")

        # Aggregate summary
        agg = _compute_aggregates(same_results, "Framework")
        st.markdown("**Aggregate (mean by framework):**")
        st.dataframe(agg, use_container_width=True, hide_index=True)

        # Per-example table
        with st.expander("Per-example details", expanded=True):
            # Format numeric columns
            display_rows = []
            for row in same_results:
                display_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        display_row[k] = round(v, 3)
                    else:
                        display_row[k] = v
                display_rows.append(display_row)

            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Triple F1": st.column_config.NumberColumn(format="%.3f"),
                    "Aligned F1": st.column_config.NumberColumn(format="%.3f"),
                    "Property F1": st.column_config.NumberColumn(format="%.3f"),
                    "Individual F1": st.column_config.NumberColumn(format="%.3f"),
                    "Literal Overlap": st.column_config.NumberColumn(format="%.3f"),
                    "Fuzzy Avg": st.column_config.NumberColumn(format="%.3f"),
                    "AST F1": st.column_config.NumberColumn(format="%.3f"),
                },
            )

        # Download as JSON
        st.download_button(
            "Download results (JSON)",
            data=json.dumps(same_results, indent=2, default=str),
            file_name="eval_same_fw_results.json",
            mime="application/json",
            key="eval_download_same",
        )

    # --- Cross-framework results ---
    if cross_results:
        st.subheader("Cross-Framework Roundtrip Results")

        # Aggregate by direction
        agg = _compute_aggregates(cross_results, "Direction")
        st.markdown("**Aggregate (mean by direction):**")
        st.dataframe(agg, use_container_width=True, hide_index=True)

        # Per-example table
        with st.expander("Per-example details", expanded=True):
            display_rows = []
            for row in cross_results:
                display_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        display_row[k] = round(v, 3)
                    else:
                        display_row[k] = v
                display_rows.append(display_row)

            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Triple F1": st.column_config.NumberColumn(format="%.3f"),
                    "Aligned F1": st.column_config.NumberColumn(format="%.3f"),
                    "Property F1": st.column_config.NumberColumn(format="%.3f"),
                    "Individual F1": st.column_config.NumberColumn(format="%.3f"),
                    "Literal Overlap": st.column_config.NumberColumn(format="%.3f"),
                    "Fuzzy Avg": st.column_config.NumberColumn(format="%.3f"),
                },
            )

        st.download_button(
            "Download results (JSON)",
            data=json.dumps(cross_results, indent=2, default=str),
            file_name="eval_cross_fw_results.json",
            mime="application/json",
            key="eval_download_cross",
        )

    # --- Extraction coverage results ---
    if coverage_results:
        st.subheader("Extraction Coverage Results")
        st.caption(
            "Measures how completely the extraction captures source code elements "
            "(agents, tasks, tools, teams, flow steps), their relationships, and "
            "string content into the ontology TTL."
        )

        # Aggregate by framework
        agg = _compute_aggregates(coverage_results, "Framework")
        st.markdown("**Aggregate (mean by framework):**")
        st.dataframe(agg, use_container_width=True, hide_index=True)

        # Per-example table
        with st.expander("Per-example details", expanded=True):
            display_rows = []
            for row in coverage_results:
                display_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        display_row[k] = round(v, 3)
                    else:
                        display_row[k] = v
                display_rows.append(display_row)

            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Overall": st.column_config.NumberColumn(format="%.3f"),
                    "Element F1": st.column_config.NumberColumn(format="%.3f"),
                    "Rel. Recall": st.column_config.NumberColumn(format="%.3f"),
                    "Content Recall": st.column_config.NumberColumn(format="%.3f"),
                    "Agents F1": st.column_config.NumberColumn(format="%.3f"),
                    "Tasks F1": st.column_config.NumberColumn(format="%.3f"),
                    "Tools F1": st.column_config.NumberColumn(format="%.3f"),
                    "Teams F1": st.column_config.NumberColumn(format="%.3f"),
                    "Steps F1": st.column_config.NumberColumn(format="%.3f"),
                },
            )

        st.download_button(
            "Download results (JSON)",
            data=json.dumps(coverage_results, indent=2, default=str),
            file_name="eval_coverage_results.json",
            mime="application/json",
            key="eval_download_coverage",
        )

    # --- Logs ---
    logs = st.session_state.get("eval_logs")
    if logs:
        with st.expander("Evaluation logs", expanded=False):
            st.code("\n".join(logs[-200:]), language="log", height=300)
