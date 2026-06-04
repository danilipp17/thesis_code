"""
gui.parallel_tab
================
Parallel-corpus evaluation tab.

For each family under ``examples/parallel/<family>/`` and each framework
variant present, runs two experiments:

1. **Extraction fidelity** — OSCIN extract on ``source_files/``, compare
   the produced TTL to the hand-authored ``ground_truth.ttl`` via
   ``ttl_pairwise`` (+ ``ttl_fuzzy_match`` when both sides parse).

2. **Generation fidelity** — OSCIN generate from ``ground_truth.ttl``
   into the same framework, compare the produced source to
   ``source_files/`` via ``ast_diff`` (+ ``syntax_validity``).

No ``mapping_conformance`` and no ``execution_trace``.

Output is cached under ``output/gui/parallel/<family>/<framework>/``
so re-renders are cheap.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import streamlit as st
from rdflib import Graph

from evaluation.metrics import ALL_METRICS, ast_diff, syntax_validity, ttl_fuzzy_match, ttl_pairwise
from evaluation.pipelines._common import (
    PROJECT_ROOT,
    StepFailed,
    default_namespace,
    default_system_name,
    resolve_source_dir,
    run_oscin,
    run_step,
)
from gui.components import (
    FRAMEWORKS,
    abox_viewer,
    ast_diff_viewer,
    capture_logs,
    fuzzy_alignment_viewer,
    source_tree_viewer,
    ttl_viewer,
)

log = logging.getLogger("oscin.eval.gui.parallel")

PARALLEL_ROOT = PROJECT_ROOT / "examples" / "parallel"
PARALLEL_OUT_ROOT = PROJECT_ROOT / "output" / "gui" / "parallel"


# ====================================================================
# Corpus discovery
# ====================================================================


def discover_families() -> list[dict[str, Any]]:
    """Return the parallel-corpus families found under ``examples/parallel/``.

    Each family entry is::

        {"family": "<name>", "variants": {fw: {"source_files": Path,
                                               "ground_truth": Path | None,
                                               "ready": bool}}}
    """
    if not PARALLEL_ROOT.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for fam_dir in sorted(p for p in PARALLEL_ROOT.iterdir() if p.is_dir()):
        variants: dict[str, dict[str, Any]] = {}
        for fw in FRAMEWORKS:
            cell = fam_dir / fw
            if not cell.is_dir():
                continue
            src = cell / "source_files"
            gt = cell / "ground_truth.ttl"
            variants[fw] = {
                "cell_dir": cell,
                "source_files": src if src.exists() else None,
                "ground_truth": gt if gt.is_file() else None,
                "ready": src.exists() and gt.is_file(),
            }
        if variants:
            out.append({"family": fam_dir.name, "variants": variants})
    return out


# ====================================================================
# Pipeline runners (in-process)
# ====================================================================


def _run_extraction(
    family: str, framework: str, source_dir: Path, ground_truth: Path, out_dir: Path
) -> dict[str, Any]:
    """Extract source -> TTL; return extraction metrics dict."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ttl_path = out_dir / "extracted.ttl"
    example_name = f"{family}_{framework}"

    report: dict[str, Any] = {
        "ttl_path": str(ttl_path),
        "ground_truth": str(ground_truth),
        "steps": {},
        "metrics": {},
    }

    try:
        run_step(
            report,
            "extract",
            run_oscin,
            [
                "extract", str(source_dir),
                "--framework", framework,
                "--system-name", default_system_name(family),
                "--namespace", default_namespace(family),
                "--output", str(ttl_path),
                "--no-report",
            ],
            _output_hint=str(ttl_path),
        )
    except StepFailed:
        return report

    try:
        report["metrics"]["ttl_pairwise"] = ttl_pairwise.compute(ground_truth, ttl_path)
    except Exception as e:
        report["metrics"]["ttl_pairwise"] = {"error": f"{type(e).__name__}: {e}"}

    try:
        g_ref = Graph(); g_ref.parse(str(ground_truth), format="turtle")
        g_cand = Graph(); g_cand.parse(str(ttl_path), format="turtle")
        report["metrics"]["ttl_fuzzy_match"] = ttl_fuzzy_match.compute(g_ref, g_cand)
    except Exception as e:
        report["metrics"]["ttl_fuzzy_match"] = {"error": f"{type(e).__name__}: {e}"}

    return report


def _run_generation(
    family: str, framework: str, ground_truth: Path, reference_source: Path, out_dir: Path
) -> dict[str, Any]:
    """Generate source from ground_truth.ttl; return generation metrics dict."""
    out_dir.mkdir(parents=True, exist_ok=True)
    gen_dir = out_dir / "generated"

    report: dict[str, Any] = {
        "gen_dir": str(gen_dir),
        "input_ttl": str(ground_truth),
        "reference_source": str(reference_source),
        "steps": {},
        "metrics": {},
    }

    try:
        run_step(
            report,
            "generate",
            run_oscin,
            [
                "generate", str(ground_truth),
                "--target-framework", framework,
                "--output-dir", str(gen_dir),
            ],
            _output_hint=str(gen_dir),
        )
    except StepFailed:
        return report

    try:
        report["metrics"]["syntax_validity"] = syntax_validity.compute(gen_dir)
    except Exception as e:
        report["metrics"]["syntax_validity"] = {"error": f"{type(e).__name__}: {e}"}

    try:
        report["metrics"]["ast_diff"] = ast_diff.compute(reference_source, gen_dir)
    except Exception as e:
        report["metrics"]["ast_diff"] = {"error": f"{type(e).__name__}: {e}"}

    return report


def run_cell(family: str, framework: str, variant: dict[str, Any]) -> dict[str, Any]:
    """Run both experiments for one (family, framework) cell."""
    out_dir = PARALLEL_OUT_ROOT / family / framework
    source_dir = variant["source_files"]
    ground_truth = variant["ground_truth"]
    if source_dir is None or ground_truth is None:
        return {"family": family, "framework": framework, "skipped": True,
                "reason": "missing source_files or ground_truth.ttl"}
    # resolve symlinks
    source_dir = Path(source_dir).resolve()
    ground_truth = Path(ground_truth).resolve()
    source_dir = resolve_source_dir(source_dir.parent) if (source_dir.parent / "source_files").is_dir() else source_dir

    extraction = _run_extraction(family, framework, source_dir, ground_truth, out_dir / "extract")
    generation = _run_generation(family, framework, ground_truth, source_dir, out_dir / "generate")

    return {
        "family": family,
        "framework": framework,
        "skipped": False,
        "extraction": extraction,
        "generation": generation,
        "out_dir": str(out_dir),
    }


# ====================================================================
# Rendering helpers
# ====================================================================


def _ttl_pairwise_row(family: str, framework: str, m: dict | None) -> dict:
    m = m or {}
    return {
        "family": family,
        "framework": framework,
        "triple_f1": m.get("triple_f1"),
        "aligned_triple_f1": m.get("aligned_triple_f1"),
        "property_f1": m.get("property_f1"),
        "individual_f1": m.get("individual_f1"),
        "literal_overlap": m.get("literal_overlap"),
    }


def _ast_row(family: str, framework: str, m: dict | None, syn: dict | None) -> dict:
    overall = (m or {}).get("overall") or {}
    per = (m or {}).get("per_feature") or {}
    return {
        "family": family,
        "framework": framework,
        "ast_overall_f1": overall.get("f1"),
        "ast_overall_precision": overall.get("precision"),
        "ast_overall_recall": overall.get("recall"),
        "ast_imports_f1": (per.get("imports") or {}).get("f1"),
        "ast_functions_f1": (per.get("functions") or {}).get("f1"),
        "ast_classes_f1": (per.get("classes") or {}).get("f1"),
        "ast_state_fields_f1": (per.get("state_fields") or {}).get("f1"),
        "ast_decorator_args_f1": (per.get("decorator_args") or {}).get("f1"),
        "syntax_rate": (syn or {}).get("syntax_rate"),
        "import_rate": (syn or {}).get("import_rate"),
    }


def _fuzzy_row(family: str, framework: str, m: dict | None) -> dict:
    m = m or {}
    return {
        "family": family,
        "framework": framework,
        "avg_score": m.get("avg_score"),
        "matched_pairs": m.get("matched_pairs"),
        "unmatched_ref": m.get("unmatched_ref"),
        "unmatched_cand": m.get("unmatched_cand"),
    }


# ====================================================================
# Main render
# ====================================================================


def render_parallel_tab() -> None:
    st.header("Parallel-corpus evaluation")
    st.caption(
        "Hand-curated 3×3 benchmark. For each (family, framework) cell, compare "
        "OSCIN-extracted TTL against the hand-authored ground-truth TTL, and "
        "OSCIN-generated source against the original source. Mapping-conformance "
        "and execution-trace are intentionally excluded."
    )

    families = discover_families()
    if not families:
        st.warning(
            f"No families found under `{PARALLEL_ROOT.relative_to(PROJECT_ROOT)}/`. "
            "Create one with `<framework>/source_files` and a hand-authored "
            "`<framework>/ground_truth.ttl`."
        )
        return

    # ----------- corpus status banner -----------
    status_rows = []
    for fam in families:
        for fw in FRAMEWORKS:
            v = fam["variants"].get(fw)
            status_rows.append({
                "family": fam["family"],
                "framework": fw,
                "source": "✓" if v and v["source_files"] else "—",
                "ground_truth": "✓" if v and v["ground_truth"] else "—",
                "ready": "✓" if v and v["ready"] else "—",
            })
    with st.expander("Corpus status", expanded=False):
        st.dataframe(status_rows, use_container_width=True, hide_index=True)

    # ----------- run controls -----------
    fam_names = [f["family"] for f in families]
    chosen_families = st.multiselect(
        "Families", options=fam_names, default=fam_names, key="par_families",
    )
    chosen_frameworks = st.multiselect(
        "Frameworks", options=list(FRAMEWORKS), default=list(FRAMEWORKS),
        key="par_frameworks",
    )
    only_ready = st.checkbox(
        "Skip cells without ground_truth.ttl",
        value=True, key="par_only_ready",
    )

    run_clicked = st.button(
        "Run parallel evaluation",
        type="primary",
        key="par_run",
        use_container_width=True,
    )

    if run_clicked:
        cells = []
        for fam in families:
            if fam["family"] not in chosen_families:
                continue
            for fw in chosen_frameworks:
                v = fam["variants"].get(fw)
                if v is None:
                    continue
                if only_ready and not v["ready"]:
                    continue
                cells.append((fam["family"], fw, v))

        if not cells:
            st.warning("Nothing to run with current filters.")
        else:
            results: list[dict] = []
            progress = st.progress(0.0, text="starting")
            with capture_logs() as cap:
                for i, (family, fw, v) in enumerate(cells):
                    progress.progress(i / len(cells), text=f"[{i+1}/{len(cells)}] {family}/{fw}")
                    try:
                        results.append(run_cell(family, fw, v))
                    except Exception as e:
                        results.append({
                            "family": family, "framework": fw, "skipped": True,
                            "reason": f"{type(e).__name__}: {e}",
                        })
                progress.progress(1.0, text="done")
            st.session_state["par_last_results"] = results
            st.session_state["par_last_logs"] = list(cap.handler.records)

    # ----------- results -----------
    results = st.session_state.get("par_last_results") or []
    if not results:
        st.info("No results yet — click *Run parallel evaluation* above.")
        return

    pairwise_rows = []
    fuzzy_rows = []
    ast_rows = []
    error_rows = []
    for r in results:
        family = r["family"]; framework = r["framework"]
        if r.get("skipped"):
            error_rows.append({
                "family": family, "framework": framework,
                "stage": "skipped", "reason": r.get("reason", ""),
            })
            continue
        ext = r["extraction"]; gen = r["generation"]
        # Pairwise / fuzzy from extraction
        pw = (ext.get("metrics") or {}).get("ttl_pairwise") or {}
        fz = (ext.get("metrics") or {}).get("ttl_fuzzy_match") or {}
        if "error" in pw:
            error_rows.append({"family": family, "framework": framework,
                               "stage": "ttl_pairwise", "reason": pw["error"]})
        else:
            pairwise_rows.append(_ttl_pairwise_row(family, framework, pw))
        if "error" in fz:
            error_rows.append({"family": family, "framework": framework,
                               "stage": "ttl_fuzzy_match", "reason": fz["error"]})
        else:
            fuzzy_rows.append(_fuzzy_row(family, framework, fz))
        # AST from generation
        ast = (gen.get("metrics") or {}).get("ast_diff") or {}
        syn = (gen.get("metrics") or {}).get("syntax_validity") or {}
        if "error" in ast:
            error_rows.append({"family": family, "framework": framework,
                               "stage": "ast_diff", "reason": ast["error"]})
        else:
            ast_rows.append(_ast_row(family, framework, ast, syn))
        # Step-level errors
        for stage, steps in (("extract", ext.get("steps") or {}),
                             ("generate", gen.get("steps") or {})):
            for name, info in steps.items():
                if not info.get("ok"):
                    error_rows.append({
                        "family": family, "framework": framework,
                        "stage": f"{stage}:{name}", "reason": info.get("error", ""),
                    })

    st.divider()
    st.subheader("Extraction fidelity — ground truth vs OSCIN-extracted")
    if pairwise_rows:
        st.dataframe(
            pairwise_rows, use_container_width=True, hide_index=True,
            column_config={
                "triple_f1":         st.column_config.NumberColumn(format="%.3f"),
                "aligned_triple_f1": st.column_config.NumberColumn(format="%.3f"),
                "property_f1":       st.column_config.NumberColumn(format="%.3f"),
                "individual_f1":     st.column_config.NumberColumn(format="%.3f"),
                "literal_overlap":   st.column_config.NumberColumn(format="%.3f"),
            },
        )
    else:
        st.caption("no pairwise results")

    with st.expander("Fuzzy-match details", expanded=False):
        if fuzzy_rows:
            st.dataframe(
                fuzzy_rows, use_container_width=True, hide_index=True,
                column_config={
                    "avg_score": st.column_config.NumberColumn(format="%.3f"),
                },
            )
        else:
            st.caption("no fuzzy results")

    st.divider()
    st.subheader("Generation fidelity — original source vs OSCIN-generated")
    if ast_rows:
        st.dataframe(
            ast_rows, use_container_width=True, hide_index=True,
            column_config={
                "ast_overall_f1":        st.column_config.NumberColumn(format="%.3f"),
                "ast_overall_precision": st.column_config.NumberColumn(format="%.3f"),
                "ast_overall_recall":    st.column_config.NumberColumn(format="%.3f"),
                "ast_imports_f1":        st.column_config.NumberColumn(format="%.3f"),
                "ast_functions_f1":      st.column_config.NumberColumn(format="%.3f"),
                "ast_classes_f1":        st.column_config.NumberColumn(format="%.3f"),
                "ast_state_fields_f1":   st.column_config.NumberColumn(format="%.3f"),
                "ast_decorator_args_f1": st.column_config.NumberColumn(format="%.3f"),
                "syntax_rate":           st.column_config.NumberColumn(format="%.3f"),
                "import_rate":           st.column_config.NumberColumn(format="%.3f"),
            },
        )
    else:
        st.caption("no AST results")

    if error_rows:
        st.divider()
        with st.expander(f"Failures / skips ({len(error_rows)})", expanded=False):
            st.dataframe(error_rows, use_container_width=True, hide_index=True)

    # ----------- side-by-side comparator -----------
    _render_side_by_side(results, families)

    logs = st.session_state.get("par_last_logs") or []
    if logs:
        with st.expander(f"Logs ({len(logs)} lines)", expanded=False):
            st.code("\n".join(logs), language="log", height=320)


# ====================================================================
# Side-by-side comparator
# ====================================================================


VIEW_OPTIONS = [
    "Original source",
    "Ground truth TTL (raw)",
    "Ground truth ABox",
    "Extracted TTL (raw)",
    "Extracted ABox",
    "Generated source",
    "ttl_pairwise",
    "ttl_fuzzy_match",
    "ast_diff",
    "syntax_validity",
]


def _cell_label(family: str, framework: str) -> str:
    return f"{family} / {framework}"


def _ready_cells(results: list[dict], families: list[dict]) -> list[tuple[str, str]]:
    """Cells that have at least source + ground-truth on disk."""
    out: list[tuple[str, str]] = []
    for fam in families:
        for fw in FRAMEWORKS:
            v = fam["variants"].get(fw)
            if v and (v["source_files"] or v["ground_truth"]):
                out.append((fam["family"], fw))
    return out


def _find_result(results: list[dict], family: str, framework: str) -> dict | None:
    for r in results:
        if r.get("family") == family and r.get("framework") == framework and not r.get("skipped"):
            return r
    return None


def _find_variant(families: list[dict], family: str, framework: str) -> dict | None:
    for fam in families:
        if fam["family"] == family:
            return fam["variants"].get(framework)
    return None


def _render_pane(
    pane_key: str,
    family: str,
    framework: str,
    view: str,
    results: list[dict],
    families: list[dict],
) -> None:
    """Render one of the two comparator panes."""
    variant = _find_variant(families, family, framework)
    result = _find_result(results, family, framework)
    src = Path(variant["source_files"]) if variant and variant["source_files"] else None
    gt = Path(variant["ground_truth"]) if variant and variant["ground_truth"] else None
    extracted = None
    gen_dir = None
    if result:
        ext_path = (result.get("extraction") or {}).get("ttl_path")
        if ext_path:
            extracted = Path(ext_path)
        gd = (result.get("generation") or {}).get("gen_dir")
        if gd:
            gen_dir = Path(gd)

    def _ttl_metric(name: str) -> None:
        if result is None:
            st.info(f"`{family}/{framework}` has not been run yet — hit *Run parallel evaluation*.")
            return
        m = (result.get("extraction") or {}).get("metrics", {}).get(name)
        if not m:
            st.caption(f"no `{name}` result for this cell")
            return
        if name == "ttl_fuzzy_match":
            fuzzy_alignment_viewer(m)
        else:
            mod = ALL_METRICS.get(name)
            if mod:
                st.markdown(mod.summarize_markdown(m))
            else:
                st.json(m)

    def _gen_metric(name: str) -> None:
        if result is None:
            st.info(f"`{family}/{framework}` has not been run yet — hit *Run parallel evaluation*.")
            return
        m = (result.get("generation") or {}).get("metrics", {}).get(name)
        if not m:
            st.caption(f"no `{name}` result for this cell")
            return
        if name == "ast_diff":
            ast_diff_viewer(m)
        else:
            mod = ALL_METRICS.get(name)
            if mod:
                st.markdown(mod.summarize_markdown(m))
            else:
                st.json(m)

    if view == "Original source":
        if src and src.is_dir():
            source_tree_viewer(src, key_suffix=pane_key)
        else:
            st.info("no `source_files/` for this cell")

    elif view == "Ground truth TTL (raw)":
        if gt and gt.is_file():
            ttl_viewer(gt, label=f"`{gt.relative_to(PROJECT_ROOT)}`")
        else:
            st.info("no `ground_truth.ttl` for this cell")

    elif view == "Ground truth ABox":
        if gt and gt.is_file():
            abox_viewer(gt, label="ABox individuals from ground truth", key_prefix=f"par_gt_{pane_key}")
        else:
            st.info("no `ground_truth.ttl` for this cell")

    elif view == "Extracted TTL (raw)":
        if extracted and extracted.is_file():
            ttl_viewer(extracted, label=f"`{extracted.relative_to(PROJECT_ROOT)}`")
        else:
            st.info("no extracted TTL — run the cell first")

    elif view == "Extracted ABox":
        if extracted and extracted.is_file():
            abox_viewer(extracted, label="ABox individuals from extracted TTL", key_prefix=f"par_ex_{pane_key}")
        else:
            st.info("no extracted TTL — run the cell first")

    elif view == "Generated source":
        if gen_dir and gen_dir.is_dir():
            source_tree_viewer(gen_dir, key_suffix=f"par_gen_{pane_key}")
        else:
            st.info("no generated source — run the cell first")

    elif view in ("ttl_pairwise", "ttl_fuzzy_match"):
        _ttl_metric(view)

    elif view in ("ast_diff", "syntax_validity"):
        _gen_metric(view)


def _render_side_by_side(results: list[dict], families: list[dict]) -> None:
    """Two-pane comparator. Each pane independently picks (family, framework, view)."""
    st.divider()
    st.subheader("Side-by-side comparison")
    st.caption(
        "Each pane independently picks family + framework + view. "
        "Use it to compare e.g. ground truth vs extracted TTL for one cell, "
        "or extracted TTL across frameworks for the same family."
    )

    cells = _ready_cells(results, families)
    if not cells:
        st.info("No cells available — corpus is empty.")
        return

    cell_labels = [_cell_label(f, w) for f, w in cells]

    # Sensible defaults: same family on both sides, GT vs extracted.
    default_left_idx = 0
    default_right_idx = 0

    col_l, col_r = st.columns(2, gap="medium")

    with col_l:
        st.markdown("**Left pane**")
        left_cell_label = st.selectbox(
            "Cell", cell_labels, index=default_left_idx,
            key="par_sxs_left_cell",
        )
        left_view = st.selectbox(
            "View", VIEW_OPTIONS,
            index=VIEW_OPTIONS.index("Ground truth TTL (raw)"),
            key="par_sxs_left_view",
        )
    with col_r:
        st.markdown("**Right pane**")
        right_cell_label = st.selectbox(
            "Cell", cell_labels, index=default_right_idx,
            key="par_sxs_right_cell",
        )
        right_view = st.selectbox(
            "View", VIEW_OPTIONS,
            index=VIEW_OPTIONS.index("Extracted TTL (raw)"),
            key="par_sxs_right_view",
        )

    left_family, left_framework = cells[cell_labels.index(left_cell_label)]
    right_family, right_framework = cells[cell_labels.index(right_cell_label)]

    with col_l:
        _render_pane("left", left_family, left_framework, left_view, results, families)
    with col_r:
        _render_pane("right", right_family, right_framework, right_view, results, families)
