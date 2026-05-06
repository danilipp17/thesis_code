"""
gui.components
==============
Shared widgets used by the Extract / Generate / Round-trip tabs.

These are intentionally small helpers — every bit of pipeline logic lives
in ``evaluation.pipelines`` and is called in-process. Nothing here touches
the filesystem outside of ``PROJECT_ROOT``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import streamlit as st

from evaluation.pipelines._common import PROJECT_ROOT

FRAMEWORKS: tuple[str, ...] = ("crewai", "langgraph", "autogen")

EXAMPLES_ROOT = PROJECT_ROOT / "examples"
FIXTURES_DIR = PROJECT_ROOT / "evaluation" / "fixtures"
EXTRACTION_OUT_ROOT = PROJECT_ROOT / "output" / "extraction"


# ---------------------------------------------------------------- framework

def framework_selector(label: str, key: str, *, default: str = "crewai") -> str:
    """Radio selector bound to one of ``FRAMEWORKS``."""
    return st.radio(
        label,
        options=FRAMEWORKS,
        index=FRAMEWORKS.index(default) if default in FRAMEWORKS else 0,
        key=key,
        horizontal=True,
    )


# ---------------------------------------------------------------- examples

def list_examples(framework: str) -> list[Path]:
    root = EXAMPLES_ROOT / framework
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir())


def example_picker(framework: str, *, key: str) -> Path | None:
    """Select-box returning the chosen example directory."""
    examples = list_examples(framework)
    if not examples:
        st.warning(f"no examples under `examples/{framework}/`")
        return None
    labels = [p.name for p in examples]
    choice = st.selectbox("Example", labels, key=key)
    return examples[labels.index(choice)]


# ---------------------------------------------------------------- ttl sources

def list_fixtures() -> list[Path]:
    if not FIXTURES_DIR.is_dir():
        return []
    return sorted(FIXTURES_DIR.glob("*.ttl"))


def list_prior_extractions() -> list[Path]:
    """All ``extracted.ttl`` files from both CLI and GUI output folders, newest first."""
    hits = []
    if EXTRACTION_OUT_ROOT.is_dir():
        hits.extend(EXTRACTION_OUT_ROOT.glob("*/*/extracted.ttl"))
        
    gui_out = PROJECT_ROOT / "output" / "gui" / "extraction"
    if gui_out.is_dir():
        hits.extend(gui_out.glob("*/*/extracted.ttl"))
        
    hits.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return hits


# ---------------------------------------------------------------- viewers

def ttl_viewer(path: Path, *, height: int = 380, label: str | None = None) -> None:
    if label:
        st.caption(label)
    if not path.is_file():
        st.info(f"no TTL at `{path}`")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    st.code(text, language="turtle", height=height)


def source_tree_viewer(root: Path, *, height: int = 380, key_suffix: str | None = None) -> None:
    """Flat listing of every file under ``root`` with click-to-view."""
    if not root.is_dir():
        st.info(f"no directory at `{root}`")
        return
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files:
        st.info(f"empty: `{root}`")
        return
    labels = [str(p.relative_to(root)) for p in files]
    widget_key = f"tree_{root}" if key_suffix is None else f"tree_{root}_{key_suffix}"
    choice = st.selectbox("File", labels, key=widget_key)
    chosen = files[labels.index(choice)]
    lang = _lang_for(chosen.suffix)
    st.code(chosen.read_text(encoding="utf-8", errors="replace"),
            language=lang, height=height)


def _lang_for(suffix: str) -> str:
    return {
        ".py": "python",
        ".ttl": "turtle",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
    }.get(suffix, "text")


# ---------------------------------------------------------------- metric card

def metric_headline(
    result: dict | None,
    field: str,
    label: str,
    *,
    help: str | None = None,
    fmt: str = "{:.3f}",
) -> None:
    """Show ``st.metric`` for a single field of a metric-result dict."""
    if not result:
        st.metric(label, "–", help=help)
        return
    value = result.get(field)
    if value is None:
        st.metric(label, "–", help=help)
        return
    if isinstance(value, (int, float)):
        st.metric(label, fmt.format(value), help=help)
    else:
        st.metric(label, str(value), help=help)


# ---------------------------------------------------------------- download

def zip_download_button(
    directory: Path,
    filename: str,
    *,
    label: str = "Download as .zip",
    key: str | None = None,
) -> None:
    """Zip ``directory`` in-memory and offer it as a download."""
    import io
    import zipfile

    if not directory.is_dir():
        st.info(f"nothing to zip at `{directory}`")
        return

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in directory.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(directory)))
    buf.seek(0)
    st.download_button(
        label=label,
        data=buf,
        file_name=filename,
        mime="application/zip",
        key=key,
    )


# ---------------------------------------------------------------- formatting

def fmt_pct(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "–"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "–"


def iter_step_errors(report: dict) -> Iterable[tuple[str, str]]:
    """Yield ``(step_name, error)`` for every failed step in ``report``."""
    for name, info in (report.get("steps") or {}).items():
        if not info.get("ok", False):
            yield name, info.get("error", "<unknown>")


# ---------------------------------------------------------------- logging

import logging


class BufferHandler(logging.Handler):
    """Collects log records into a list so the GUI can render them after the run."""

    def __init__(self, level: int = logging.INFO) -> None:
        super().__init__(level=level)
        self.records: list[str] = []
        self.setFormatter(logging.Formatter("%(levelname)-7s %(name)s  %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            self.records.append(self.format(record))
        except Exception:
            pass


class capture_logs:
    """Context manager: attach a ``BufferHandler`` to OSCIN loggers."""

    def __init__(self, logger_names: Iterable[str] = ("oscin", "oscin.eval")) -> None:
        self._names = list(logger_names)
        self.handler = BufferHandler()
        self._loggers: list[logging.Logger] = []
        self._prev_levels: list[int] = []

    def __enter__(self) -> "capture_logs":
        for name in self._names:
            lg = logging.getLogger(name)
            self._loggers.append(lg)
            self._prev_levels.append(lg.level)
            if lg.level > logging.INFO or lg.level == logging.NOTSET:
                lg.setLevel(logging.INFO)
            lg.addHandler(self.handler)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for lg, prev in zip(self._loggers, self._prev_levels):
            lg.removeHandler(self.handler)
            lg.setLevel(prev)


# ---------------------------------------------------------------- recent runs

def list_recent_runs(pipeline: str, *, limit: int = 5) -> list[Path]:
    """Most-recent run directories under ``output/gui/<pipeline>/`` with a report."""
    root = PROJECT_ROOT / "output" / "gui" / pipeline
    if not root.is_dir():
        return []
    reports = list(root.glob("*/*/report.json"))
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [r.parent for r in reports[:limit]]


# ---------------------------------------------------------------- fuzzy alignment

def fuzzy_alignment_viewer(result: dict) -> None:
    """Renders the alignment, missing, and extra items as a unified dataframe."""
    alignment = result.get("alignment") or {}
    missing_ref = result.get("missing_ref") or {}
    extra_cand = result.get("extra_cand") or {}
    
    rows = []
    
    classes = sorted(set(alignment) | set(missing_ref) | set(extra_cand))
    for cls in classes:
        for ref_loc, cand_loc, score in alignment.get(cls, []):
            rows.append({
                "Class": cls,
                "TTL 1 (Ref)": ref_loc,
                "TTL 2 (Cand)": cand_loc,
                "Score": score,
                "Status": "✅ Matched",
            })
            
        for ref_loc in missing_ref.get(cls, []):
            rows.append({
                "Class": cls,
                "TTL 1 (Ref)": ref_loc,
                "TTL 2 (Cand)": "–",
                "Score": "–",
                "Status": "❌ Missing in TTL2",
            })
            
        for cand_loc in extra_cand.get(cls, []):
            rows.append({
                "Class": cls,
                "TTL 1 (Ref)": "–",
                "TTL 2 (Cand)": cand_loc,
                "Score": "–",
                "Status": "⚠️ Extra in TTL2",
            })
            
    if not rows:
        st.info("No ABox individuals found to compare.")
        return
        
    st.dataframe(rows, use_container_width=True)


# ---------------------------------------------------------------- ast semantics

def ast_diff_viewer(result: dict) -> None:
    """Renders the missing, extra, and matched AST structures as a unified dataframe."""
    per_feature = result.get("per_feature") or {}
    rows = []
    
    # Preferred ordering of features
    key_order = ["imports", "functions", "classes", "class_bases", "decorators", "decorator_args", "state_fields", "state_annotations", "graph_calls"]
    keys = [k for k in key_order if k in per_feature] + [k for k in per_feature if k not in key_order]
    
    for feature_type in keys:
        data = per_feature[feature_type]
        for item in data.get("matched", []):
            rows.append({
                "AST Feature": feature_type,
                "Element Signature": str(item),
                "Status": "✅ Matched",
            })
        for item in data.get("missing", []):
            rows.append({
                "AST Feature": feature_type,
                "Element Signature": str(item),
                "Status": "❌ Missing in Generated Code",
            })
        for item in data.get("extra", []):
            rows.append({
                "AST Feature": feature_type,
                "Element Signature": str(item),
                "Status": "⚠️ Extra in Generated Code",
            })
            
    if not rows:
        st.info("No AST features found to compare.")
        return
        
    st.dataframe(rows, use_container_width=True)


# ---------------------------------------------------------------- abox browser

def _local_name(uri) -> str:
    """Extract the local name from a URI (after # or last /)."""
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s


def abox_viewer(ttl_path: Path, *, label: str | None = None, key_prefix: str = "abox") -> None:
    """Parse a TTL file and display ABox individuals in an individual-focused layout.

    Each individual gets its own expander (grouped by OWL class) showing a
    compact property table inside. This avoids the 5-rows-per-individual
    clutter of a flat table.
    """
    from collections import defaultdict
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDF, OWL, RDFS

    if label:
        st.caption(label)
    if not ttl_path.is_file():
        st.info(f"No TTL at `{ttl_path}`")
        return

    try:
        g = Graph()
        g.parse(str(ttl_path), format="turtle")
    except Exception as e:
        st.error(f"Failed to parse TTL: {type(e).__name__}: {e}")
        return

    # Identify TBox namespace(s) to exclude schema-level subjects.
    from oscin.namespaces import is_ontology_uri

    # Gather all ABox individuals: subjects that have rdf:type and whose
    # URI does NOT start with any imported ontology namespace.
    # Map: class_name -> [(subj_uri, subj_local)]
    class_to_individuals: dict[str, list[tuple[str, str]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()  # deduplicate (uri, class)

    for s, _, o in g.triples((None, RDF.type, None)):
        if not isinstance(s, URIRef):
            continue
        if is_ontology_uri(s):
            continue
        # Skip OWL/RDFS meta-types
        if isinstance(o, URIRef) and str(o).startswith(("http://www.w3.org/2002/07/owl#",
                                                         "http://www.w3.org/2000/01/rdf-schema#")):
            continue
        cls = _local_name(o)
        key = (str(s), cls)
        if key not in seen:
            seen.add(key)
            class_to_individuals[cls].append((str(s), _local_name(s)))

    if not class_to_individuals:
        st.info("No ABox individuals found in this TTL.")
        return

    skip_predicates = {str(RDF.type), str(OWL.imports), str(RDFS.label)}

    total_individuals = sum(len(v) for v in class_to_individuals.values())
    st.markdown(f"**{total_individuals}** individuals across **{len(class_to_individuals)}** classes")

    for cls in sorted(class_to_individuals):
        members = class_to_individuals[cls]
        st.subheader(f"{cls}  ({len(members)})")

        for subj_uri, subj_local in sorted(members, key=lambda x: x[1]):
            props: list[dict[str, str]] = []
            for _, p, o in g.triples((URIRef(subj_uri), None, None)):
                if str(p) in skip_predicates:
                    continue
                prop_name = _local_name(p)
                if isinstance(o, Literal):
                    val = str(o)[:200]
                elif isinstance(o, URIRef):
                    val = _local_name(o)
                else:
                    val = str(o)[:200]
                props.append({"Property": prop_name, "Value": val})

            n_props = len(props)
            with st.expander(f"`{subj_local}`  — {n_props} properties"):
                if props:
                    st.dataframe(props, use_container_width=True, hide_index=True)
                else:
                    st.caption("no data properties")
