"""
fuzzy_match.py
==============
Entity alignment across two ontology graphs via fuzzy name/literal matching.

The existing ``oscin.evaluator.compute_pairwise`` compares individuals by
*exact* local name within a class. When the extractor and a reference (or
the generator and a re-extractor) produce the same entity under different
URIs — e.g. ``Task_filter_emails`` vs ``filter_emails_task_output`` —
exact matching under-counts. This module computes a best-effort alignment
using stdlib ``difflib.SequenceMatcher`` and, when available, ``rapidfuzz``.

The alignment is a dict::

    {
        "LLMAgent": [
            ("ref_local_name", "cand_local_name", score: float),
            ...
        ],
        "Task": [...],
        ...
    }

Downstream metrics can rewrite candidate local-names to their matched
reference counterparts before computing precision/recall, which lifts
naming noise out of the score.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Iterable

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from oscin.namespaces import AGENTOSCIN

log = logging.getLogger("oscin.eval.fuzzy")

NAME = "ttl_fuzzy_match"

# Properties that carry human-readable labels worth using as alignment signal.
LABEL_PROPERTIES = [
    AGENTOSCIN.hasTitle,
    AGENTOSCIN.agentRole,
    AGENTOSCIN.agentID,
    AGENTOSCIN.hasDescription,
]

# Classes we care about aligning. Others fall back to local-name only.
ALIGNABLE_CLASSES = {
    "LLMAgent", "Agent", "Task", "Tool", "Team", "WorkflowStep",
    "StartStep", "EndStep", "ConditionalStep", "Orchestration",
    "Prompt", "Goal", "AgenticSystem",
}


def _local(uri) -> str:
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace/underscores for similarity."""
    return " ".join(text.lower().replace("_", " ").split())


def _similarity(a: str, b: str) -> float:
    """Symmetric similarity in [0, 1] based on normalized forms."""
    a_n, b_n = _normalize(a), _normalize(b)
    if not a_n or not b_n:
        return 0.0
    if a_n == b_n:
        return 1.0
    ratio = SequenceMatcher(None, a_n, b_n).ratio()
    # Token overlap bonus — helps with reorderings ("filter emails" vs "emails filter").
    a_tokens = set(a_n.split())
    b_tokens = set(b_n.split())
    if a_tokens and b_tokens:
        jacc = len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
        ratio = max(ratio, jacc)
    return ratio


def _collect_labels(g: Graph, subject: URIRef) -> list[str]:
    labels = []
    for prop in LABEL_PROPERTIES:
        for _, _, o in g.triples((subject, prop, None)):
            if isinstance(o, Literal):
                s = str(o).strip()
                if s:
                    labels.append(s)
    return labels


def _score_pair(
    ref_local: str, ref_labels: list[str],
    cand_local: str, cand_labels: list[str],
) -> float:
    """Best similarity over (local, label) cross-product."""
    scores = [_similarity(ref_local, cand_local)]
    for rl in ref_labels:
        scores.append(_similarity(rl, cand_local))
        for cl in cand_labels:
            scores.append(_similarity(rl, cl))
    for cl in cand_labels:
        scores.append(_similarity(ref_local, cl))
    return max(scores) if scores else 0.0


def _individuals_by_class(g: Graph) -> dict[str, list[URIRef]]:
    result: dict[str, list[URIRef]] = defaultdict(list)
    for s, _, o in g.triples((None, RDF.type, None)):
        if not isinstance(s, URIRef):
            continue
        if not isinstance(o, URIRef):
            continue
        if str(s).startswith(str(AGENTOSCIN)):
            continue  # TBox subject
        cls = _local(o)
        if cls in ALIGNABLE_CLASSES:
            result[cls].append(s)
    return dict(result)


def align(
    reference: Graph,
    candidate: Graph,
    threshold: float = 0.55,
) -> dict[str, list[tuple[str, str, float]]]:
    """
    Compute per-class fuzzy alignment between reference and candidate.

    Greedy matching: within each class, repeatedly pick the highest-scoring
    (ref, cand) pair whose score >= threshold; remove both from consideration;
    continue until no pair meets threshold.

    Returns ``{class_name: [(ref_local, cand_local, score), ...]}``.
    Unmatched individuals do not appear in the alignment.
    """
    ref_by_class = _individuals_by_class(reference)
    cand_by_class = _individuals_by_class(candidate)

    alignment: dict[str, list[tuple[str, str, float]]] = {}

    for cls in sorted(set(ref_by_class) | set(cand_by_class)):
        refs = ref_by_class.get(cls, [])
        cands = cand_by_class.get(cls, [])
        if not refs or not cands:
            continue

        # Pre-compute labels once per subject.
        ref_info = [(r, _local(r), _collect_labels(reference, r)) for r in refs]
        cand_info = [(c, _local(c), _collect_labels(candidate, c)) for c in cands]

        # Build pairwise score matrix.
        pairs: list[tuple[float, int, int]] = []
        for i, (_, rloc, rlabels) in enumerate(ref_info):
            for j, (_, cloc, clabels) in enumerate(cand_info):
                s = _score_pair(rloc, rlabels, cloc, clabels)
                if s >= threshold:
                    pairs.append((s, i, j))
        pairs.sort(reverse=True)

        used_ref: set[int] = set()
        used_cand: set[int] = set()
        class_alignment: list[tuple[str, str, float]] = []
        for score, i, j in pairs:
            if i in used_ref or j in used_cand:
                continue
            class_alignment.append(
                (ref_info[i][1], cand_info[j][1], round(score, 3))
            )
            used_ref.add(i)
            used_cand.add(j)

        if class_alignment:
            alignment[cls] = class_alignment

    return alignment


def summary(alignment: dict[str, list[tuple[str, str, float]]]) -> dict:
    """Produce a compact JSON-serializable summary of the alignment."""
    per_class = {}
    total_pairs = 0
    total_score = 0.0
    for cls, pairs in alignment.items():
        per_class[cls] = {
            "matched": len(pairs),
            "avg_score": round(sum(s for _, _, s in pairs) / len(pairs), 3)
            if pairs else 0.0,
            "pairs": [
                {"ref": r, "cand": c, "score": s} for r, c, s in pairs
            ],
        }
        total_pairs += len(pairs)
        total_score += sum(s for _, _, s in pairs)

    return {
        "total_matched_pairs": total_pairs,
        "avg_score": round(total_score / total_pairs, 3) if total_pairs else 0.0,
        "by_class": per_class,
    }


def compute(reference: Graph, candidate: Graph, threshold: float = 0.55) -> dict:
    """Top-level entry point for the metric harness."""
    alignment = align(reference, candidate, threshold=threshold)
    return {
        "metric": NAME,
        "threshold": threshold,
        **summary(alignment),
        "alignment": alignment,  # kept for downstream P/R re-scoring
    }


def row(result: dict) -> dict:
    """Flat fields for the benchmark CSV."""
    return {
        "fuzzy_matched_pairs": result.get("total_matched_pairs"),
        "fuzzy_avg_score": result.get("avg_score"),
    }


def summarize_markdown(result: dict) -> str:
    if "error" in result:
        return f"## Fuzzy alignment\n- error: `{result['error']}`\n"
    lines = ["## Fuzzy alignment (TTL₁ ↔ TTL₂)"]
    lines.append(f"- matched pairs: {result.get('total_matched_pairs')}")
    lines.append(f"- avg score: {result.get('avg_score')}")
    by_class = result.get("by_class") or {}
    for cls in sorted(by_class):
        info = by_class[cls]
        lines.append(
            f"  - {cls}: {info.get('matched')} matched, avg={info.get('avg_score')}"
        )
    return "\n".join(lines) + "\n"


def rewrite_with_alignment(
    triples: Iterable[tuple[str, str, str]],
    alignment: dict[str, list[tuple[str, str, float]]],
    direction: str = "cand_to_ref",
) -> set[tuple[str, str, str]]:
    """
    Rewrite normalized triples (subject/predicate/object-local-name form)
    using the alignment so that paired entities share a name.

    direction='cand_to_ref': rename candidate locals to reference locals.
    Useful before intersecting candidate vs reference triple sets.
    """
    mapping: dict[str, str] = {}
    for _cls, pairs in alignment.items():
        for ref_name, cand_name, _ in pairs:
            if direction == "cand_to_ref":
                mapping[cand_name] = ref_name
            else:
                mapping[ref_name] = cand_name

    out = set()
    for s, p, o in triples:
        out.add((mapping.get(s, s), p, mapping.get(o, o)))
    return out
