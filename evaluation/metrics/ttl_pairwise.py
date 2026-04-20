"""
ttl_pairwise.py
===============
Thin adapter around :func:`oscin.evaluator.compute_pairwise`.

Compares two TTL graphs by individual/property/triple/literal P/R/F1.
Used by:

- the roundtrip pipeline (TTL₁ vs TTL₂ to measure ontology idempotence),
- the extraction pipeline (extracted vs ground-truth, when a ground-truth
  TTL ships with the example),
- the generation pipeline (re-extracted output vs input TTL, when the
  input came from a previous extraction).
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from rdflib import Graph

from oscin.evaluator import compute_pairwise as _compute_pairwise

NAME = "ttl_pairwise"


def compute(reference_ttl: Path | str, candidate_ttl: Path | str) -> dict:
    """Load both TTLs and return the pairwise metrics as a dict."""
    try:
        g_ref = Graph()
        g_ref.parse(str(reference_ttl), format="turtle")
        g_cand = Graph()
        g_cand.parse(str(candidate_ttl), format="turtle")
    except Exception as e:
        return {"metric": NAME, "error": f"{type(e).__name__}: {e}"}

    m = _compute_pairwise(g_ref, g_cand)
    d = asdict(m)
    d["metric"] = NAME
    d["reference"] = str(reference_ttl)
    d["candidate"] = str(candidate_ttl)
    return d


def compute_from_graphs(reference: Graph, candidate: Graph) -> dict:
    """Variant that takes already-loaded ``rdflib.Graph`` objects."""
    m = _compute_pairwise(reference, candidate)
    d = asdict(m)
    d["metric"] = NAME
    return d


def row(result: dict) -> dict:
    """Flat fields for the benchmark CSV."""
    return {
        "triple_f1": result.get("triple_f1"),
        "triple_precision": result.get("triple_precision"),
        "triple_recall": result.get("triple_recall"),
        "property_f1": result.get("property_f1"),
        "individual_f1": result.get("individual_f1"),
        "literal_overlap": result.get("literal_overlap"),
    }


def summarize_markdown(result: dict) -> str:
    if "error" in result:
        return f"## TTL pairwise comparison\n- error: `{result['error']}`\n"
    lines = ["## TTL pairwise (reference vs candidate)"]
    for level in ("individual", "property", "triple"):
        p = result.get(f"{level}_precision")
        r = result.get(f"{level}_recall")
        f = result.get(f"{level}_f1")
        if p is not None:
            lines.append(
                f"- **{level}**: P={p:.3f} R={r:.3f} F1={f:.3f}"
            )
    lo = result.get("literal_overlap")
    if lo is not None:
        lines.append(f"- **literal_overlap**: {lo:.3f}")
    missing = result.get("missing_properties") or []
    extra = result.get("extra_properties") or []
    if missing:
        lines.append(f"- missing properties ({len(missing)}): "
                     + ", ".join(missing[:10])
                     + ("…" if len(missing) > 10 else ""))
    if extra:
        lines.append(f"- extra properties ({len(extra)}): "
                     + ", ".join(extra[:10])
                     + ("…" if len(extra) > 10 else ""))
    return "\n".join(lines) + "\n"
