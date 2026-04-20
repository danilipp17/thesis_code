"""
ttl_intrinsic.py
================
Thin adapter around :func:`oscin.evaluator.compute_intrinsic`.

The intrinsic metric describes a **single** TTL graph in isolation: how
many individuals per class, how many distinct properties are exercised,
triples-per-individual density, literal vs object-link split. Produced by
the extraction and generation pipelines as a sanity check and to fill
the "this extraction/generation exists and is non-trivial" row in the
benchmark.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from rdflib import Graph

from oscin.evaluator import compute_intrinsic as _compute_intrinsic

NAME = "ttl_intrinsic"


def compute(ttl_path: Path | str) -> dict:
    """Load a TTL file and return its intrinsic metrics as a dict."""
    try:
        g = Graph()
        g.parse(str(ttl_path), format="turtle")
    except Exception as e:
        return {"metric": NAME, "error": f"{type(e).__name__}: {e}"}

    m = _compute_intrinsic(g)
    d = asdict(m)
    # `properties_used` is a set; make it JSON-friendly.
    if "properties_used" in d and isinstance(d["properties_used"], set):
        d["properties_used"] = sorted(d["properties_used"])
    d["metric"] = NAME
    d["source"] = str(ttl_path)
    return d


def row(result: dict) -> dict:
    """Flat fields for the benchmark CSV."""
    return {
        "intrinsic_triples": result.get("total_triples"),
        "intrinsic_abox_triples": result.get("abox_triples"),
        "intrinsic_individuals": result.get("total_individuals"),
        "intrinsic_properties": result.get("property_count"),
        "intrinsic_density": (
            round(result.get("information_density") or 0.0, 3)
        ),
    }


def summarize_markdown(result: dict) -> str:
    if "error" in result:
        return f"## Intrinsic metrics\n- error: `{result['error']}`\n"
    lines = [
        "## Intrinsic metrics (single TTL)",
        f"- source: `{result.get('source')}`",
        f"- total triples: {result.get('total_triples')}",
        f"- ABox triples: {result.get('abox_triples')}",
        f"- individuals: {result.get('total_individuals')}",
        f"- properties used: {result.get('property_count')}",
        f"- information density: "
        f"{round(result.get('information_density') or 0.0, 3)} triples/indiv",
        f"- literals / object-links: "
        f"{result.get('literals_count')} / {result.get('object_links_count')}",
    ]
    counts = result.get("individual_counts") or {}
    if counts:
        lines.append("- individuals by class:")
        for cls, n in sorted(counts.items()):
            lines.append(f"  - {cls}: {n}")
    return "\n".join(lines) + "\n"
