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

import streamlit as st
import evaluation  # noqa: F401  (eager import confirms project root is on path)

from evaluation.pipelines._common import PROJECT_ROOT
from evaluation.metrics import ALL_METRICS
from evaluation.pipelines.extraction import run_extraction
from evaluation.pipelines.generation import run_generation
from evaluation.pipelines.roundtrip import run_roundtrip
from evaluation.reporting import render_markdown
from gui.components import (
    capture_logs,
    example_picker,
    framework_selector,
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

GUI_OUT_ROOT = PROJECT_ROOT / "output" / "gui"

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

tab_extract, tab_generate, tab_roundtrip = st.tabs(
    ["Extract", "Generate", "Round-trip"]
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
        with st.spinner(f"extracting {fw}/{example.name} …"), capture_logs() as cap:
            try:
                report = run_extraction(example, fw, out_root=out_root)
            except Exception as e:  # defensive; pipelines usually catch
                st.error(f"{type(e).__name__}: {e}")
                report = None

        if report is not None:
            st.session_state["extract_last_report"] = report
            st.session_state["extract_last_logs"] = list(cap.handler.records)

    report = st.session_state.get("extract_last_report")
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

        # TTL viewer + report markdown + logs
        ttl_tab, md_tab, log_tab = st.tabs(
            ["Extracted TTL", "Full report", "Logs"]
        )
        with ttl_tab:
            ttl_path = Path(report["work_dir"]) / "extracted.ttl"
            ttl_viewer(ttl_path, label=f"`{ttl_path}`")
        with md_tab:
            st.markdown(render_markdown(report))
        with log_tab:
            logs = st.session_state.get("extract_last_logs") or []
            if logs:
                st.code("\n".join(logs), language="log", height=420)
            else:
                st.caption("no captured logs")

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
                    "no prior extractions found at `output/extraction/*/*/extracted.ttl` "
                    "— run the Extract tab first."
                )
            else:
                labels = [
                    f"{p.parent.parent.name}/{p.parent.name}" for p in prior
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

        gen_tab, md_tab, log_tab = st.tabs(
            ["Generated source", "Full report", "Logs"]
        )
        with gen_tab:
            gen_dir = Path(report["work_dir"]) / "generated"
            source_tree_viewer(gen_dir)
            if gen_dir.is_dir():
                zip_download_button(
                    gen_dir,
                    filename=f"{report['example']}_{target_fw}.zip",
                    key="gen_download",
                )
        with md_tab:
            st.markdown(render_markdown(report))
        with log_tab:
            logs = st.session_state.get("gen_last_logs") or []
            if logs:
                st.code("\n".join(logs), language="log", height=420)
            else:
                st.caption("no captured logs")

with tab_roundtrip:
    st.header("Source → TTL → Source")
    st.caption(
        "Extract, regenerate, and re-extract — measuring how much "
        "survives the ontology round-trip."
    )

    col_left, col_right = st.columns([1, 2], gap="large")
    with col_left:
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
        out_root = GUI_OUT_ROOT / "roundtrip"
        with st.spinner(
            f"round-tripping {rt_src_fw}/{rt_example.name} → {rt_tgt_fw} …"
        ), capture_logs() as cap:
            try:
                report = run_roundtrip(
                    rt_example,
                    rt_src_fw,
                    target_framework=rt_tgt_fw if is_cross else None,
                    skip_execution=st.session_state.get("rt_skip_exec", True),
                    execution_timeout=float(st.session_state.get("rt_exec_timeout", 120)),
                    out_root=out_root,
                )
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")
                report = None

        if report is not None:
            st.session_state["rt_last_report"] = report
            st.session_state["rt_last_logs"] = list(cap.handler.records)

    report = st.session_state.get("rt_last_report")
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
            cols = st.columns(3)
            with cols[0]:
                metric_headline(m_pair, "triple_f1", "TTL triple F1")
            with cols[1]:
                metric_headline(m_fuzzy, "avg_score", "Fuzzy avg")
            with cols[2]:
                metric_headline(
                    m_map, "overall_score", "Mapping conformance",
                    help="crewai ↔ langgraph mapping rule coverage.",
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

        # Per-metric detail tabs — one tab per metric that produced a result
        metric_names = [n for n in metrics.keys() if n in ALL_METRICS]
        if metric_names:
            metric_tabs = st.tabs(
                metric_names + ["TTL₁", "TTL₂", "Full report", "Logs"]
            )
            for i, name in enumerate(metric_names):
                with metric_tabs[i]:
                    mod = ALL_METRICS[name]
                    try:
                        st.markdown(mod.summarize_markdown(metrics[name]))
                    except Exception as e:
                        st.error(f"render error: {type(e).__name__}: {e}")

            # TTL₁ / TTL₂ viewers + full report + logs
            work = Path(report["work_dir"])
            with metric_tabs[len(metric_names)]:
                ttl_viewer(work / "ttl1.ttl", label="TTL₁ (first extraction)")
            with metric_tabs[len(metric_names) + 1]:
                ttl_viewer(work / "ttl2.ttl", label="TTL₂ (re-extraction)")
            with metric_tabs[len(metric_names) + 2]:
                st.markdown(render_markdown(report))
            with metric_tabs[len(metric_names) + 3]:
                logs = st.session_state.get("rt_last_logs") or []
                if logs:
                    st.code("\n".join(logs), language="log", height=420)
                else:
                    st.caption("no captured logs")
