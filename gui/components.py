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
    """All ``output/extraction/<fw>/<name>/extracted.ttl`` files, newest first."""
    if not EXTRACTION_OUT_ROOT.is_dir():
        return []
    hits = list(EXTRACTION_OUT_ROOT.glob("*/*/extracted.ttl"))
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


def source_tree_viewer(root: Path, *, height: int = 380) -> None:
    """Flat listing of every file under ``root`` with click-to-view."""
    if not root.is_dir():
        st.info(f"no directory at `{root}`")
        return
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files:
        st.info(f"empty: `{root}`")
        return
    labels = [str(p.relative_to(root)) for p in files]
    choice = st.selectbox("File", labels, key=f"tree_{root}")
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
