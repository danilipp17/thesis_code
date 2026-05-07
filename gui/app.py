"""
gui.app
=======
Streamlit entry point.

Run from the project root inside ``.venv``:

    streamlit run gui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# ``streamlit run gui/app.py`` puts ``gui/`` on sys.path, not the project root.
# The ``evaluation`` and ``gui`` packages live at the project root but aren't
# pip-installed (only ``oscin`` is), so prepend the project root here before
# importing them.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import re

import streamlit as st
import evaluation  # noqa: F401  (eager import confirms project root is on path)

from evaluation.pipelines._common import PROJECT_ROOT, default_namespace
from evaluation.metrics import ALL_METRICS, ttl_intrinsic, ttl_pairwise
from evaluation.pipelines.extraction import run_extraction
from evaluation.pipelines.generation import run_generation
from evaluation.pipelines.hybrid_roundtrip import run_hybrid_roundtrip
from evaluation.pipelines.roundtrip import run_roundtrip
from evaluation.reporting import render_markdown
from gui.components import (
    capture_logs,
    example_picker,
    framework_selector,
    fuzzy_alignment_viewer,
    ast_diff_viewer,
    abox_viewer,
    iter_step_errors,
    list_fixtures,
    list_prior_extractions,
    list_recent_runs,
    metric_headline,
    source_tree_viewer,
    ttl_viewer,
    zip_download_button,
    FRAMEWORKS,
)
from gui.evaluation_tab import render_evaluation_tab
from oscin.llm_extractor import run_llm_extraction

GUI_OUT_ROOT = PROJECT_ROOT / "output" / "gui"
GUI_LLM_OUT_ROOT = PROJECT_ROOT / "output" / "gui" / "extraction_llm"

OPENAI_MODELS: tuple[str, ...] = (
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
)


def _safe_dir_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = cleaned.strip("._-")
    return cleaned if cleaned else "model"


def _normalize_models(selected: list[str], custom: str) -> list[str]:
    models = [m.strip() for m in selected if m and m.strip()]
    if custom:
        for m in custom.split(","):
            if m.strip():
                models.append(m.strip())
    seen: set[str] = set()
    out: list[str] = []
    for m in models:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _extract_roundtrip_metrics(report: dict | None) -> dict:
    if not report:
        return {}
    metrics = report.get("metrics") or {}
    pw = metrics.get("ttl_pairwise") or {}
    return {
        "triple_f1": pw.get("triple_f1"),
        "aligned_triple_f1": pw.get("aligned_triple_f1"),
        "property_f1": pw.get("property_f1"),
        "individual_f1": pw.get("individual_f1"),
        "literal_overlap": pw.get("literal_overlap"),
    }


def _run_llm_extraction_compare(
    source_dir: Path,
    *,
    framework: str,
    example_name: str,
    models: list[str],
    use_cache: bool,
    ast_ttl_path: Path | None,
    ground_truth: Path | None,
) -> list[dict]:
    results: list[dict] = []
    ns = default_namespace(example_name)

    for model in models:
        safe_model = _safe_dir_name(model)
        work = GUI_LLM_OUT_ROOT / framework / example_name / safe_model
        work.mkdir(parents=True, exist_ok=True)
        ttl_path = work / "extracted_llm.ttl"

        try:
            if not use_cache or not ttl_path.is_file():
                run_llm_extraction(
                    source_dir=source_dir,
                    output_path=ttl_path,
                    instance_namespace=ns,
                    provider="openai",
                    model=model,
                )

            metrics: dict[str, dict] = {
                "ttl_intrinsic": ttl_intrinsic.compute(ttl_path),
            }
            if ast_ttl_path and ast_ttl_path.is_file():
                metrics["llm_vs_ast"] = ttl_pairwise.compute(ast_ttl_path, ttl_path)
            else:
                metrics["llm_vs_ast"] = {
                    "metric": "ttl_pairwise",
                    "error": "AST TTL not available",
                }
            if ground_truth and ground_truth.is_file():
                metrics["llm_vs_ground_truth"] = ttl_pairwise.compute(ground_truth, ttl_path)

            results.append({
                "model": model,
                "provider": "openai",
                "work_dir": str(work),
                "ttl_path": str(ttl_path),
                "metrics": metrics,
                "status": "ok",
            })
        except Exception as e:
            results.append({
                "model": model,
                "provider": "openai",
                "work_dir": str(work),
                "ttl_path": str(ttl_path),
                "metrics": {},
                "status": f"error: {type(e).__name__}: {e}",
            })

    return results

st.set_page_config(
    page_title="OSCIN — Transformation GUI",
    page_icon=None,
    layout="wide",
)


# ================================================================ sidebar

with st.sidebar:
    st.title("OSCIN")
    st.caption("Ontology-driven Source Code Interoperability")
    st.divider()
    st.markdown("**Project root**")
    st.code(str(PROJECT_ROOT), language="text")
    st.divider()
    st.markdown(
        "Use the tabs to run one of the three pipelines. "
        "Outputs are written under `output/gui/<pipeline>/<name>/`."
    )

    st.divider()
    st.markdown("**Recent runs**")
    for pipeline in ("extraction", "generation", "roundtrip"):
        runs = list_recent_runs(pipeline, limit=5)
        if not runs:
            continue
        with st.expander(pipeline, expanded=False):
            for d in runs:
                # Path layout is output/gui/<pipeline>/<fw>/<name>
                label = f"{d.parent.name}/{d.name}"
                st.code(label, language="text")


# ================================================================ main

st.title("OSCIN transformation front-end")

tab_extract, tab_generate, tab_roundtrip, tab_evaluate = st.tabs(
    ["Extract", "Generate", "Round-trip", "Evaluate"]
)

with tab_extract:
    st.header("Source → TTL")
    st.caption(
        "Parse an example source tree into the shared ontology. "
        "If `ground_truth.ttl` sits next to the example, pairwise and "
        "fuzzy-match metrics are added automatically."
    )

    col_left, col_right = st.columns([1, 2], gap="large")
    with col_left:
        fw = framework_selector("Framework", key="extract_fw")
        example = example_picker(fw, key=f"extract_example_{fw}")

        with st.expander("LLM extraction compare", expanded=False):
            llm_compare = st.checkbox(
                "Compare LLM extraction",
                value=False,
                key="extract_llm_compare",
                help="Run LLM extraction and compare TTL metrics against AST extraction.",
            )
            llm_models = st.multiselect(
                "OpenAI models",
                options=OPENAI_MODELS,
                default=["gpt-4o"],
                key="extract_llm_models",
            )
            llm_custom = st.text_input(
                "Custom models (comma-separated)",
                value="",
                key="extract_llm_models_custom",
            )
            llm_use_cache = st.checkbox(
                "Use cached LLM outputs",
                value=True,
                key="extract_llm_use_cache",
                help="Reuse existing LLM TTL outputs if they exist.",
            )
        run_clicked = st.button(
            "Run extraction",
            type="primary",
            disabled=example is None,
            key="extract_run",
            use_container_width=True,
        )

    with col_right:
        if example is not None:
            st.markdown(f"**Selected example:** `examples/{fw}/{example.name}/`")
            gt = example / "ground_truth.ttl"
            if gt.is_file():
                st.success(f"ground truth found: `{gt.relative_to(PROJECT_ROOT)}`")
            else:
                st.caption("no ground truth TTL — only intrinsic metrics will run")

    if run_clicked and example is not None:
        out_root = GUI_OUT_ROOT / "extraction"
        llm_results: list[dict] | None = None

        with st.spinner(f"extracting {fw}/{example.name} …"), capture_logs() as cap:
            try:
                report = run_extraction(example, fw, out_root=out_root)
            except Exception as e:  # defensive; pipelines usually catch
                st.error(f"{type(e).__name__}: {e}")
                report = None

            if report is not None and llm_compare:
                models = _normalize_models(llm_models, llm_custom)
                if not models:
                    st.warning("No LLM models selected.")
                else:
                    try:
                        source_dir = Path(report.get("source_dir") or "")
                        ast_ttl = Path(report["work_dir"]) / "extracted.ttl"
                        gt = Path(report.get("ground_truth")) if report.get("ground_truth") else None
                        llm_results = _run_llm_extraction_compare(
                            source_dir,
                            framework=fw,
                            example_name=example.name,
                            models=models,
                            use_cache=st.session_state.get("extract_llm_use_cache", True),
                            ast_ttl_path=ast_ttl,
                            ground_truth=gt,
                        )
                    except Exception as e:
                        st.error(f"LLM compare failed: {type(e).__name__}: {e}")

        if report is not None:
            st.session_state["extract_last_report"] = report
            st.session_state["extract_last_logs"] = list(cap.handler.records)
            st.session_state["extract_last_llm_results"] = llm_results

    report = st.session_state.get("extract_last_report")
    llm_results = st.session_state.get("extract_last_llm_results")
    if report:
        st.divider()

        # Step-error banner
        errs = list(iter_step_errors(report))
        if errs:
            for step_name, err in errs:
                st.error(f"step `{step_name}` failed: {err}")

        metrics = report.get("metrics") or {}

        # Metric cards row
        m_int = metrics.get("ttl_intrinsic")
        m_pair = metrics.get("ttl_pairwise")
        m_fuzzy = metrics.get("ttl_fuzzy_match")

        cols = st.columns(4)
        with cols[0]:
            metric_headline(m_int, "total_triples", "Triples", fmt="{:.0f}")
        with cols[1]:
            metric_headline(m_int, "total_individuals", "Individuals", fmt="{:.0f}")
        with cols[2]:
            metric_headline(
                m_pair, "triple_f1", "Triple F1",
                help="Against ground_truth.ttl (if present).",
            )
        with cols[3]:
            metric_headline(
                m_fuzzy, "avg_score", "Fuzzy avg",
                help="Average per-pair similarity across aligned individuals.",
            )

        # Side-by-side viewer
        view_options = ["Source code", "Extracted ABox", "Extracted TTL", "Full report", "Logs"]
        if llm_results:
            view_options.append("LLM TTL")
        side_l, side_r = st.columns(2, gap="medium")

        with side_l:
            left_view = st.selectbox("Left pane", view_options, index=0, key="extract_left_view")
        with side_r:
            right_view = st.selectbox("Right pane", view_options, index=1, key="extract_right_view")

        def _render_extraction_pane(view_name: str, col_key: str) -> None:
            if view_name == "Source code":
                src = report.get("source_dir")
                if src:
                    source_tree_viewer(Path(src), key_suffix=f"extract_{col_key}")
                else:
                    st.info("No source directory recorded.")
            elif view_name == "Extracted ABox":
                ttl_path = Path(report["work_dir"]) / "extracted.ttl"
                abox_viewer(ttl_path, label="ABox individuals from extracted TTL", key_prefix=f"extract_abox_{col_key}")
            elif view_name == "Extracted TTL":
                ttl_path = Path(report["work_dir"]) / "extracted.ttl"
                ttl_viewer(ttl_path, label=f"`{ttl_path}`")
            elif view_name == "Full report":
                st.markdown(render_markdown(report))
            elif view_name == "Logs":
                logs = st.session_state.get("extract_last_logs") or []
                if logs:
                    st.code("\n".join(logs), language="log", height=420)
                else:
                    st.caption("no captured logs")
            elif view_name == "LLM TTL":
                if not llm_results:
                    st.info("No LLM results found.")
                    return
                model_labels = [r.get("model", "model") for r in llm_results]
                model_choice = st.selectbox(
                    "LLM model",
                    model_labels,
                    key=f"extract_llm_view_{col_key}",
                )
                chosen = llm_results[model_labels.index(model_choice)]
                ttl_path = Path(chosen.get("ttl_path") or "")
                if ttl_path.is_file():
                    ttl_viewer(ttl_path, label=f"LLM TTL ({model_choice})")
                else:
                    st.info("LLM TTL not found.")

        with side_l:
            _render_extraction_pane(left_view, "left")
        with side_r:
            _render_extraction_pane(right_view, "right")

        # LLM comparison summary
        if llm_results:
            st.divider()
            st.subheader("LLM vs AST extraction")
            rows = []
            for r in llm_results:
                metrics = r.get("metrics") or {}
                llm_vs_ast = metrics.get("llm_vs_ast") or {}
                llm_vs_gt = metrics.get("llm_vs_ground_truth") or {}
                rows.append({
                    "Model": r.get("model"),
                    "Status": r.get("status"),
                    "LLM vs AST Triple F1": llm_vs_ast.get("triple_f1"),
                    "LLM vs AST Aligned F1": llm_vs_ast.get("aligned_triple_f1"),
                    "LLM vs AST Property F1": llm_vs_ast.get("property_f1"),
                    "LLM vs AST Individual F1": llm_vs_ast.get("individual_f1"),
                    "LLM vs AST Literal Overlap": llm_vs_ast.get("literal_overlap"),
                    "LLM vs GT Triple F1": llm_vs_gt.get("triple_f1"),
                    "LLM vs GT Aligned F1": llm_vs_gt.get("aligned_triple_f1"),
                    "LLM vs GT Property F1": llm_vs_gt.get("property_f1"),
                    "LLM vs GT Individual F1": llm_vs_gt.get("individual_f1"),
                    "LLM vs GT Literal Overlap": llm_vs_gt.get("literal_overlap"),
                })

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "LLM vs AST Triple F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs AST Aligned F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs AST Property F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs AST Individual F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs AST Literal Overlap": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs GT Triple F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs GT Aligned F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs GT Property F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs GT Individual F1": st.column_config.NumberColumn(format="%.3f"),
                    "LLM vs GT Literal Overlap": st.column_config.NumberColumn(format="%.3f"),
                },
            )

with tab_generate:
    st.header("TTL → Source")
    st.caption(
        "Render an OWL/TTL description back into framework source code. "
        "Pick an input TTL from a fixture, a prior extraction, or by upload."
    )

    col_left, col_right = st.columns([1, 2], gap="large")

    with col_left:
        target_fw = framework_selector("Target framework", key="gen_target_fw")

        source_mode = st.radio(
            "Input TTL source",
            options=("Fixture", "Prior extraction", "Upload"),
            key="gen_source_mode",
            horizontal=False,
        )

        input_ttl_path: Path | None = None
        fixture_name: str | None = None
        derived_name: str | None = None

        if source_mode == "Fixture":
            fixtures = list_fixtures()
            if not fixtures:
                st.warning("no fixtures found under `evaluation/fixtures/`")
            else:
                labels = [p.stem for p in fixtures]
                choice = st.selectbox("Fixture", labels, key="gen_fixture")
                fixture_name = choice
                derived_name = choice
                input_ttl_path = fixtures[labels.index(choice)]

        elif source_mode == "Prior extraction":
            prior = list_prior_extractions()
            if not prior:
                st.warning(
                    "No prior extractions found at `output/extraction/` or `output/gui/extraction/` "
                    "— run the Extract tab first."
                )
            else:
                labels = [
                    f"{'[GUI]' if 'gui' in p.parts else '[CLI]'} {p.parent.parent.name}/{p.parent.name}" for p in prior
                ]
                choice = st.selectbox("Prior extraction", labels, key="gen_prior")
                input_ttl_path = prior[labels.index(choice)]
                derived_name = input_ttl_path.parent.name

        else:  # Upload
            uploaded = st.file_uploader(
                "Upload a .ttl file",
                type=["ttl"],
                key="gen_upload",
            )
            if uploaded is not None:
                upload_dir = GUI_OUT_ROOT / "generation" / "_uploads"
                upload_dir.mkdir(parents=True, exist_ok=True)
                tmp = upload_dir / uploaded.name
                tmp.write_bytes(uploaded.getvalue())
                input_ttl_path = tmp
                derived_name = tmp.stem

        with st.expander("Advanced", expanded=False):
            reextract = st.checkbox(
                "Re-extract generated code (ontology idempotence)",
                value=False,
                key="gen_reextract",
                help="Extract the generated source back to TTL and compute pairwise F1 "
                     "against the input TTL.",
            )
            execute = st.checkbox(
                "Execute generated code (requires .env / API keys)",
                value=False,
                key="gen_execute",
                help="Runs the generated entrypoint via subprocess. Incurs real API "
                     "calls if the target code hits an LLM.",
            )
            st.caption(
                "Both options add significant runtime. Keep them off for a quick preview."
            )

        run_gen = st.button(
            "Run generation",
            type="primary",
            disabled=input_ttl_path is None,
            key="gen_run",
            use_container_width=True,
        )

    with col_right:
        if input_ttl_path is not None:
            rel = (
                input_ttl_path.relative_to(PROJECT_ROOT)
                if str(input_ttl_path).startswith(str(PROJECT_ROOT))
                else input_ttl_path
            )
            st.markdown(f"**Input TTL:** `{rel}`")
            st.markdown(f"**Target:** `{target_fw}`")

    if run_gen and input_ttl_path is not None:
        out_root = GUI_OUT_ROOT / "generation"
        with st.spinner(
            f"generating {target_fw} from {input_ttl_path.name} …"
        ), capture_logs() as cap:
            try:
                report = run_generation(
                    ttl=None if fixture_name else input_ttl_path,
                    fixture=fixture_name,
                    target_framework=target_fw,
                    execute=st.session_state.get("gen_execute", False),
                    reextract=st.session_state.get("gen_reextract", False),
                    out_root=out_root,
                    name=derived_name,
                )
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")
                report = None

        if report is not None:
            st.session_state["gen_last_report"] = report
            st.session_state["gen_last_logs"] = list(cap.handler.records)

    report = st.session_state.get("gen_last_report")
    if report:
        st.divider()

        for step_name, err in iter_step_errors(report):
            st.error(f"step `{step_name}` failed: {err}")

        metrics = report.get("metrics") or {}
        m_syn = metrics.get("syntax_validity")
        m_pair = metrics.get("ttl_pairwise")
        m_exec = metrics.get("execution_trace")

        cols = st.columns(4)
        with cols[0]:
            metric_headline(
                m_syn, "syntax_rate", "Syntax OK",
                help="Fraction of generated .py files that parse cleanly.",
            )
        with cols[1]:
            metric_headline(
                m_syn, "import_rate", "Imports OK",
                help="Fraction of top-level imports that resolve.",
            )
        with cols[2]:
            metric_headline(
                m_pair, "triple_f1", "Re-extract F1",
                help="Input TTL vs re-extraction of generated code.",
            )
        with cols[3]:
            ok_match = (m_exec or {}).get("ok_match")
            if ok_match is None:
                st.metric("Execution", "–", help="Enable 'Execute generated code' in Advanced.")
            else:
                st.metric("Execution", "✓" if ok_match else "✗",
                          help="Generated code exits with same status as reference.")

        # Side-by-side viewer
        gen_view_options = ["Generated source", "Input ABox", "Full report", "Logs"]
        side_l, side_r = st.columns(2, gap="medium")

        with side_l:
            left_view = st.selectbox("Left pane", gen_view_options, index=0, key="gen_left_view")
        with side_r:
            right_view = st.selectbox("Right pane", gen_view_options, index=1, key="gen_right_view")

        def _render_gen_pane(view_name: str, col_key: str) -> None:
            if view_name == "Generated source":
                gen_dir = Path(report["work_dir"]) / "generated"
                source_tree_viewer(gen_dir, key_suffix=f"gen_{col_key}")
                if gen_dir.is_dir():
                    zip_download_button(
                        gen_dir,
                        filename=f"{report['example']}_{target_fw}.zip",
                        key=f"gen_download_{col_key}",
                    )
            elif view_name == "Input ABox":
                input_ttl = report.get("input_ttl")
                if input_ttl:
                    abox_viewer(Path(input_ttl), label=f"ABox individuals from `{Path(input_ttl).name}`", key_prefix=f"gen_abox_{col_key}")
                else:
                    st.info("No input TTL path recorded in report.")
            elif view_name == "Full report":
                st.markdown(render_markdown(report))
            elif view_name == "Logs":
                logs = st.session_state.get("gen_last_logs") or []
                if logs:
                    st.code("\n".join(logs), language="log", height=420)
                else:
                    st.caption("no captured logs")

        with side_l:
            _render_gen_pane(left_view, "left")
        with side_r:
            _render_gen_pane(right_view, "right")

with tab_roundtrip:
    st.header("Source → TTL → Source")
    st.caption(
        "Extract, regenerate, and re-extract — measuring how much "
        "survives the ontology round-trip."
    )

    col_left, col_right = st.columns([1, 2], gap="large")
    with col_left:
        rt_mode = st.radio(
            "Round-trip mode",
            options=[
                "Deterministic (AST)",
                "Hybrid (AST + LLM fixup)",
                "Compare (AST vs Hybrid)",
            ],
            key="rt_mode",
            horizontal=False,
        )
        rt_src_fw = framework_selector(
            "Source framework", key="rt_src_fw", default="crewai"
        )
        rt_example = example_picker(rt_src_fw, key=f"rt_example_{rt_src_fw}")
        rt_tgt_fw = st.selectbox(
            "Target framework",
            options=FRAMEWORKS,
            index=FRAMEWORKS.index(rt_src_fw),
            key="rt_tgt_fw",
            help="Same as source ⇒ ast_diff + execution_trace. "
                 "Different ⇒ mapping_conformance (only for crewai↔langgraph).",
        )
        is_cross = (rt_tgt_fw != rt_src_fw)

        with st.expander("Advanced", expanded=False):
            skip_exec = st.checkbox(
                "Skip execution trace (same-fw only)",
                value=True,
                key="rt_skip_exec",
                help="Executing both sides can take >1 min and needs API keys.",
            )
            exec_timeout = st.slider(
                "Execution timeout (s)",
                min_value=30, max_value=300, value=120, step=15,
                key="rt_exec_timeout",
            )
            if rt_mode in ("Hybrid (AST + LLM fixup)", "Compare (AST vs Hybrid)"):
                st.markdown("**LLM Fixup (OpenAI)**")
                rt_llm_models = st.multiselect(
                    "OpenAI models",
                    options=OPENAI_MODELS,
                    default=["gpt-4o"],
                    key="rt_llm_models",
                )
                rt_llm_custom = st.text_input(
                    "Custom models (comma-separated)",
                    value="",
                    key="rt_llm_models_custom",
                )

        rt_run = st.button(
            "Run round-trip",
            type="primary",
            disabled=rt_example is None,
            key="rt_run",
            use_container_width=True,
        )

    with col_right:
        if rt_example is not None:
            flow = (
                f"`{rt_src_fw}` ── extract ──▶ TTL₁ ── "
                f"generate({rt_tgt_fw}) ──▶ `{rt_tgt_fw}` ── extract ──▶ TTL₂"
            )
            st.markdown(f"**Flow:** {flow}")
            if is_cross:
                st.info(
                    "Cross-framework mode: AST/execution metrics are dropped "
                    "(different languages). `mapping_conformance` runs only for "
                    "crewai ↔ langgraph."
                )

    if rt_run and rt_example is not None:
        det_report = None
        hybrid_report = None
        out_root_det = GUI_OUT_ROOT / "roundtrip"
        out_root_hybrid = GUI_OUT_ROOT / "roundtrip_hybrid"
        mode_label = {
            "Deterministic (AST)": "deterministic",
            "Hybrid (AST + LLM fixup)": "hybrid",
            "Compare (AST vs Hybrid)": "compare",
        }.get(rt_mode, "deterministic")

        with st.spinner(
            f"round-tripping {rt_src_fw}/{rt_example.name} → {rt_tgt_fw} ({mode_label}) …"
        ), capture_logs() as cap:
            try:
                if rt_mode in ("Deterministic (AST)", "Compare (AST vs Hybrid)"):
                    det_report = run_roundtrip(
                        rt_example,
                        rt_src_fw,
                        target_framework=rt_tgt_fw if is_cross else None,
                        skip_execution=st.session_state.get("rt_skip_exec", True),
                        execution_timeout=float(st.session_state.get("rt_exec_timeout", 120)),
                        out_root=out_root_det,
                    )

                if rt_mode in ("Hybrid (AST + LLM fixup)", "Compare (AST vs Hybrid)"):
                    models = _normalize_models(
                        st.session_state.get("rt_llm_models", ["gpt-4o"]),
                        st.session_state.get("rt_llm_models_custom", ""),
                    )
                    if not models:
                        st.error("No LLM model selected for hybrid fixup.")
                    else:
                        hybrid_report = run_hybrid_roundtrip(
                            rt_example,
                            rt_src_fw,
                            target_framework=rt_tgt_fw if is_cross else None,
                            skip_execution=st.session_state.get("rt_skip_exec", True),
                            execution_timeout=float(st.session_state.get("rt_exec_timeout", 120)),
                            llm_provider="openai",
                            llm_model=models[0],
                            out_root=out_root_hybrid,
                        )
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")

        st.session_state["rt_last_report"] = det_report if rt_mode != "Hybrid (AST + LLM fixup)" else hybrid_report
        st.session_state["rt_last_hybrid_report"] = hybrid_report
        st.session_state["rt_last_logs"] = list(cap.handler.records)

    report = st.session_state.get("rt_last_report")
    hybrid_report = st.session_state.get("rt_last_hybrid_report")
    if report:
        st.divider()
        for step_name, err in iter_step_errors(report):
            st.error(f"step `{step_name}` failed: {err}")

        metrics = report.get("metrics") or {}

        # Headline cards — chosen per mode
        if report.get("mode") == "cross_framework":
            m_pair = metrics.get("ttl_pairwise")
            m_fuzzy = metrics.get("ttl_fuzzy_match")
            m_map = metrics.get("mapping_conformance")
            m_ast = metrics.get("ast_diff")
            cols = st.columns(4)
            with cols[0]:
                metric_headline(m_pair, "triple_f1", "TTL triple F1")
            with cols[1]:
                metric_headline(m_fuzzy, "avg_score", "Fuzzy avg")
            with cols[2]:
                metric_headline(
                    m_map, "overall_score", "Mapping conformance",
                    help="crewai ↔ langgraph mapping rule coverage.",
                )
            with cols[3]:
                ast_f1 = ((m_ast or {}).get("overall") or {}).get("f1")
                st.metric(
                    "AST F1",
                    f"{ast_f1:.3f}" if isinstance(ast_f1, (int, float)) else "–",
                    help="AST feature F1 across source vs generated.",
                )
        else:
            m_pair = metrics.get("ttl_pairwise")
            m_fuzzy = metrics.get("ttl_fuzzy_match")
            m_ast = metrics.get("ast_diff")
            m_exec = metrics.get("execution_trace")
            cols = st.columns(4)
            with cols[0]:
                metric_headline(m_pair, "triple_f1", "TTL triple F1")
            with cols[1]:
                metric_headline(m_fuzzy, "avg_score", "Fuzzy avg")
            with cols[2]:
                ast_f1 = ((m_ast or {}).get("overall") or {}).get("f1")
                st.metric(
                    "AST F1",
                    f"{ast_f1:.3f}" if isinstance(ast_f1, (int, float)) else "–",
                    help="AST feature F1 across source vs generated.",
                )
            with cols[3]:
                ok_match = (m_exec or {}).get("ok_match")
                if m_exec and m_exec.get("skipped"):
                    st.metric("Execution", "skipped")
                elif ok_match is None:
                    st.metric("Execution", "–")
                else:
                    st.metric("Execution", "✓" if ok_match else "✗")

        if hybrid_report and report is not hybrid_report:
            st.divider()
            st.subheader("Hybrid vs Deterministic (AST)")
            det_metrics = _extract_roundtrip_metrics(report)
            hyb_metrics = _extract_roundtrip_metrics(hybrid_report)
            rows = []
            for key in (
                "triple_f1",
                "aligned_triple_f1",
                "property_f1",
                "individual_f1",
                "literal_overlap",
            ):
                det_val = det_metrics.get(key)
                hyb_val = hyb_metrics.get(key)
                delta = None
                if isinstance(det_val, (int, float)) and isinstance(hyb_val, (int, float)):
                    delta = hyb_val - det_val
                rows.append({
                    "Metric": key,
                    "Deterministic": det_val,
                    "Hybrid": hyb_val,
                    "Delta": delta,
                })
            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Deterministic": st.column_config.NumberColumn(format="%.3f"),
                    "Hybrid": st.column_config.NumberColumn(format="%.3f"),
                    "Delta": st.column_config.NumberColumn(format="%+.3f"),
                },
            )

        # Side-by-side viewer
        work = Path(report["work_dir"])
        hybrid_work = Path(hybrid_report["work_dir"]) if hybrid_report else None
        rt_view_options = ["Original source", "TTL₁ ABox", "TTL₂ ABox", "Generated source", "TTL₁ raw", "TTL₂ raw", "Full report", "Logs"]
        if hybrid_report:
            rt_view_options = [
                "Hybrid Generated source",
                "Hybrid TTL₂ ABox",
                "Hybrid TTL₂ raw",
            ] + rt_view_options

        # Add metric-specific views
        metric_names = [n for n in metrics.keys() if n in ALL_METRICS]
        rt_view_options = metric_names + rt_view_options

        side_l, side_r = st.columns(2, gap="medium")

        with side_l:
            left_view = st.selectbox("Left pane", rt_view_options, index=0, key="rt_left_view")
        with side_r:
            right_idx = min(1, len(rt_view_options) - 1)
            right_view = st.selectbox("Right pane", rt_view_options, index=right_idx, key="rt_right_view")

        def _render_rt_pane(view_name: str, col_key: str) -> None:
            if view_name == "Original source":
                src = report.get("source_dir")
                if src:
                    source_tree_viewer(Path(src), key_suffix=f"rt_orig_{col_key}")
                else:
                    st.info("No source directory recorded.")
            elif view_name == "Hybrid Generated source":
                if hybrid_work:
                    gen_dir = hybrid_work / "generated_fixed"
                    source_tree_viewer(gen_dir, key_suffix=f"rt_hybrid_{col_key}")
                else:
                    st.info("No hybrid output directory recorded.")
            elif view_name == "Hybrid TTL₂ ABox":
                if hybrid_work:
                    abox_viewer(hybrid_work / "ttl2.ttl", label="ABox from TTL₂ (hybrid fixup)", key_prefix=f"rt_hybrid_abox_{col_key}")
                else:
                    st.info("No hybrid output directory recorded.")
            elif view_name == "Hybrid TTL₂ raw":
                if hybrid_work:
                    ttl_viewer(hybrid_work / "ttl2.ttl", label="TTL₂ (hybrid fixup)")
                else:
                    st.info("No hybrid output directory recorded.")
            elif view_name == "TTL₁ ABox":
                abox_viewer(work / "ttl1.ttl", label="ABox from TTL₁ (first extraction)", key_prefix=f"rt_abox1_{col_key}")
            elif view_name == "TTL₂ ABox":
                abox_viewer(work / "ttl2.ttl", label="ABox from TTL₂ (re-extraction)", key_prefix=f"rt_abox2_{col_key}")
            elif view_name == "Generated source":
                gen_dir = work / "generated"
                source_tree_viewer(gen_dir, key_suffix=f"rt_{col_key}")
            elif view_name == "TTL₁ raw":
                ttl_viewer(work / "ttl1.ttl", label="TTL₁ (first extraction)")
            elif view_name == "TTL₂ raw":
                ttl_viewer(work / "ttl2.ttl", label="TTL₂ (re-extraction)")
            elif view_name == "Full report":
                st.markdown(render_markdown(report))
            elif view_name == "Logs":
                logs = st.session_state.get("rt_last_logs") or []
                if logs:
                    st.code("\n".join(logs), language="log", height=420)
                else:
                    st.caption("no captured logs")
            elif view_name in metric_names:
                # Render the metric-specific view
                if view_name == "ttl_fuzzy_match":
                    fuzzy_alignment_viewer(metrics[view_name])
                elif view_name == "ast_diff":
                    ast_diff_viewer(metrics[view_name])
                else:
                    mod = ALL_METRICS[view_name]
                    try:
                        st.markdown(mod.summarize_markdown(metrics[view_name]))
                    except Exception as e:
                        st.error(f"render error: {type(e).__name__}: {e}")

        with side_l:
            _render_rt_pane(left_view, "left")
        with side_r:
            _render_rt_pane(right_view, "right")

with tab_evaluate:
    render_evaluation_tab()
