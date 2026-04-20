"""
evaluation.pipelines._common
============================
Utilities shared by the three pipeline drivers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from oscin.cli import main as oscin_main

log = logging.getLogger("oscin.eval.pipeline")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_oscin(argv: list[str]) -> None:
    """Invoke ``oscin.cli.main`` in-process; translate ``SystemExit`` to raise."""
    try:
        oscin_main(argv)
    except SystemExit as e:
        if e.code not in (0, None):
            raise RuntimeError(f"oscin {' '.join(argv)} exited {e.code}")


def resolve_source_dir(example_root: Path) -> Path:
    """
    Resolve an example directory to the directory that actually contains
    Python source. Convention: ``examples/<fw>/<name>/source_files/``;
    some examples (e.g. ``autogen/comprehensive``) have a flat layout
    where ``main.py`` sits directly under the example root.
    """
    if (example_root / "source_files").is_dir():
        return example_root / "source_files"
    return example_root


def default_namespace(name: str) -> str:
    return f"http://example.org/{name.replace('-', '_')}#"


def default_system_name(name: str) -> str:
    return name.replace("-", "_")


def run_step(report: dict, step_name: str, fn, *args, **kwargs):
    """
    Execute a pipeline step, record ok/error into ``report['steps']``,
    and return the function result (or raise ``StepFailed`` on error).

    The driver-only ``_output_hint`` kwarg is popped before calling ``fn``
    and only appears in the report metadata.
    """
    output_hint = kwargs.pop("_output_hint", None)
    try:
        result = fn(*args, **kwargs)
        report.setdefault("steps", {})[step_name] = {
            "ok": True,
            "output": output_hint or "",
        }
        return result
    except Exception as e:
        report.setdefault("steps", {})[step_name] = {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
        }
        raise StepFailed(step_name) from e


class StepFailed(Exception):
    """Raised by ``run_step`` when a step fails; drivers catch this to
    stop the pipeline without losing the partial report."""
