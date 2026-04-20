"""
evaluation.reporting
====================
Shared report-rendering utilities.

A "report" is a plain dict with this schema:

    {
        "pipeline": str,                  # "extraction" | "generation" | "roundtrip"
        "example": str,
        "framework": str,                 # source framework
        "target_framework": str | None,   # only for generation / cross-fw roundtrip
        "work_dir": str,
        "steps": {step_name: {"ok": bool, "output"?: str, "error"?: str}},
        "metrics": {metric_name: <result dict>},
    }

``render_markdown`` walks the report and delegates per-metric rendering
to ``evaluation.metrics.<name>.summarize_markdown``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.metrics import ALL_METRICS


# --------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------


def render_markdown(report: dict) -> str:
    """Render a pipeline report as markdown."""
    pipeline = report.get("pipeline", "?")
    fw = report.get("framework", "?")
    ex = report.get("example", "?")
    title = f"# {pipeline.title()} — {fw}/{ex}"

    tgt = report.get("target_framework")
    lines = [title, ""]
    lines.append(f"- source: `{report.get('source_dir', '?')}`")
    if tgt and tgt != fw:
        lines.append(f"- target framework: `{tgt}`")
    lines.append(f"- work dir: `{report.get('work_dir', '?')}`")
    lines.append("")

    steps = report.get("steps") or {}
    if steps:
        lines.append("## Pipeline")
        for step_name, info in steps.items():
            ok = "✓" if info.get("ok") else "✗"
            extra = info.get("output") or info.get("error") or ""
            lines.append(f"- `{step_name}` {ok} {extra}")
        lines.append("")

    metrics = report.get("metrics") or {}
    for metric_name, result in metrics.items():
        mod = ALL_METRICS.get(metric_name)
        if mod is None:
            # Unknown metric — dump JSON for visibility.
            lines.append(f"## {metric_name}")
            lines.append("```json")
            lines.append(json.dumps(result, indent=2, default=str)[:2000])
            lines.append("```")
            lines.append("")
            continue
        try:
            block = mod.summarize_markdown(result)
        except Exception as e:  # defensive
            block = f"## {metric_name}\n- render error: `{type(e).__name__}: {e}`\n"
        lines.append(block)

    return "\n".join(lines) + "\n"


def build_row(report: dict) -> dict[str, Any]:
    """Flatten every metric's ``row()`` output into a single dict for CSV."""
    out: dict[str, Any] = {
        "pipeline": report.get("pipeline"),
        "framework": report.get("framework"),
        "target_framework": report.get("target_framework"),
        "example": report.get("example"),
    }
    metrics = report.get("metrics") or {}
    for metric_name, result in metrics.items():
        mod = ALL_METRICS.get(metric_name)
        if mod is None or not hasattr(mod, "row"):
            continue
        try:
            out.update(mod.row(result))
        except Exception:
            pass

    errors: list[str] = []
    for step_name, info in (report.get("steps") or {}).items():
        if not info.get("ok"):
            errors.append(f"{step_name}:{info.get('error', '?')}")
    for metric_name, result in metrics.items():
        if isinstance(result, dict) and "error" in result:
            errors.append(f"{metric_name}:{result['error']}")
    out["errors"] = " | ".join(errors) if errors else ""
    return out


def write_report(report: dict, work_dir: Path) -> None:
    """Persist report.json and report.md next to one another."""
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "report.json").write_text(
        json.dumps(report, indent=2, default=str)
    )
    (work_dir / "report.md").write_text(render_markdown(report))
