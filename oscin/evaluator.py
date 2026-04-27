"""
evaluator.py
============
Automated evaluation metrics for ontology extraction quality.

Compares extracted ontology instances against a reference (gold standard)
or evaluates a single extraction in isolation. Designed for comparing
the AST-based extraction pipeline against the LLM-based baseline.

Metrics
-------
**Single-file (intrinsic):**
- Individual count by OWL class
- Property coverage (which ontology properties are exercised)
- ABox triple count (instance triples only, excluding TBox)
- Information density (ABox triples per individual)

**Pairwise (reference-based):**
- Individual-level precision / recall / F1 (by class type)
- Property-level precision / recall / F1 (which properties are populated)
- Triple-level similarity (semantic overlap)
- Content fidelity (literal value overlap for shared individuals)

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from oscin.namespaces import AGENTOSCIN

log = logging.getLogger("oscin")

# TBox predicates to exclude from ABox analysis
TBOX_PREDICATES = {
    RDF.type,  # kept for individual counting, but filtered for some metrics
    RDFS.subClassOf,
    RDFS.subPropertyOf,
    RDFS.domain,
    RDFS.range,
    OWL.imports,
}

# Classes that belong to the TBox (schema), not ABox (instances)
TBOX_TYPES = {
    OWL.Class,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.Ontology,
    OWL.AllDisjointClasses,
}


# ===================================================================
# Data structures
# ===================================================================

@dataclass
class IntrinsicMetrics:
    """Metrics for a single extraction file."""
    total_triples: int = 0
    abox_triples: int = 0
    individual_counts: dict[str, int] = field(default_factory=dict)
    total_individuals: int = 0
    properties_used: set[str] = field(default_factory=set)
    property_count: int = 0
    information_density: float = 0.0
    literals_count: int = 0
    object_links_count: int = 0


@dataclass
class PairwiseMetrics:
    """Metrics comparing a candidate extraction against a reference."""
    # Individual-level (by class)
    individual_precision: float = 0.0
    individual_recall: float = 0.0
    individual_f1: float = 0.0
    individual_detail: dict[str, dict[str, float]] = field(default_factory=dict)

    # Property-level
    property_precision: float = 0.0
    property_recall: float = 0.0
    property_f1: float = 0.0

    # Triple-level (normalized semantic triples — exact local-name match)
    triple_precision: float = 0.0
    triple_recall: float = 0.0
    triple_f1: float = 0.0

    # Triple-level (after class-aware bipartite alignment of individuals)
    aligned_triple_precision: float = 0.0
    aligned_triple_recall: float = 0.0
    aligned_triple_f1: float = 0.0
    alignment_size: int = 0  # number of cand individuals matched to a ref

    # Content fidelity
    literal_overlap: float = 0.0

    # Missing / extra
    missing_individuals: list[str] = field(default_factory=list)
    extra_individuals: list[str] = field(default_factory=list)
    missing_properties: list[str] = field(default_factory=list)
    extra_properties: list[str] = field(default_factory=list)


# ===================================================================
# Helper functions
# ===================================================================

def _is_tbox_triple(s, p, o) -> bool:
    """Check if a triple is a TBox (schema) assertion."""
    if p in (RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range):
        return True
    if p == RDF.type and o in TBOX_TYPES:
        return True
    if isinstance(s, URIRef) and str(s).startswith(str(AGENTOSCIN)):
        # Triples where the subject is an ontology-level URI (not instance)
        if p == RDF.type and o in TBOX_TYPES:
            return True
        if p in (RDFS.subClassOf, RDFS.subPropertyOf):
            return True
    return False


def _is_abox_individual(s, o, g: Graph) -> bool:
    """Check if a subject is an ABox individual (not a TBox class/property)."""
    for _, _, type_obj in g.triples((s, RDF.type, None)):
        if type_obj in TBOX_TYPES:
            return False
    return True


def _local_name(uri) -> str:
    """Extract the local name from a URI."""
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s


def _class_name(uri) -> str:
    """Extract the class name from an agentoscin URI."""
    return _local_name(uri)


def _get_abox_individuals(g: Graph) -> dict[str, set[str]]:
    """
    Get all ABox individuals grouped by class type.
    Returns {class_name: {individual_local_name, ...}}.
    """
    result: dict[str, set[str]] = defaultdict(set)
    for s, _, o in g.triples((None, RDF.type, None)):
        if o in TBOX_TYPES:
            continue
        if isinstance(s, URIRef) and not str(s).startswith(str(AGENTOSCIN)):
            result[_class_name(o)].add(_local_name(s))
    return dict(result)


def _get_used_properties(g: Graph) -> set[str]:
    """Get all agentoscin properties used in ABox triples."""
    props = set()
    for s, p, o in g:
        if _is_tbox_triple(s, p, o):
            continue
        p_str = str(p)
        if str(AGENTOSCIN) in p_str:
            props.add(_local_name(p))
    return props


def _get_abox_triples(g: Graph) -> int:
    """Count ABox triples only."""
    count = 0
    for s, p, o in g:
        if _is_tbox_triple(s, p, o):
            continue
        # Skip triples where subject is an ontology-level URI
        if isinstance(s, URIRef) and str(s).startswith(str(AGENTOSCIN)):
            continue
        count += 1
    return count


def _get_normalized_triples(g: Graph) -> set[tuple[str, str, str]]:
    """
    Normalize ABox triples to (subject_local, predicate_local, object_repr)
    for comparison. Object is either a local name (URI) or literal value.
    """
    triples = set()
    for s, p, o in g:
        if _is_tbox_triple(s, p, o):
            continue
        if isinstance(s, URIRef) and str(s).startswith(str(AGENTOSCIN)):
            continue

        s_name = _local_name(s) if isinstance(s, URIRef) else str(s)
        p_name = _local_name(p) if isinstance(p, URIRef) else str(p)

        if isinstance(o, Literal):
            o_repr = f'"{str(o)}"'
        elif isinstance(o, URIRef):
            o_repr = _local_name(o)
        else:
            o_repr = str(o)

        triples.add((s_name, p_name, o_repr))
    return triples


def _get_literal_values(g: Graph) -> set[str]:
    """Collect all literal string values from ABox triples."""
    values = set()
    for s, p, o in g:
        if _is_tbox_triple(s, p, o):
            continue
        if isinstance(s, URIRef) and str(s).startswith(str(AGENTOSCIN)):
            continue
        if isinstance(o, Literal) and str(o).strip():
            # Normalize whitespace for comparison
            values.add(" ".join(str(o).split()).lower())
    return values


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ===================================================================
# Core evaluation functions
# ===================================================================

def compute_intrinsic(g: Graph) -> IntrinsicMetrics:
    """Compute intrinsic metrics for a single graph."""
    m = IntrinsicMetrics()

    m.total_triples = len(g)
    m.abox_triples = _get_abox_triples(g)

    individuals = _get_abox_individuals(g)
    m.individual_counts = {k: len(v) for k, v in sorted(individuals.items())}
    m.total_individuals = sum(len(v) for v in individuals.values())

    m.properties_used = _get_used_properties(g)
    m.property_count = len(m.properties_used)

    m.information_density = (
        m.abox_triples / m.total_individuals if m.total_individuals > 0 else 0.0
    )

    # Count literals vs object links
    for s, p, o in g:
        if _is_tbox_triple(s, p, o):
            continue
        if isinstance(s, URIRef) and str(s).startswith(str(AGENTOSCIN)):
            continue
        if isinstance(o, Literal):
            m.literals_count += 1
        elif isinstance(o, URIRef):
            m.object_links_count += 1

    return m


def compute_pairwise(reference: Graph, candidate: Graph) -> PairwiseMetrics:
    """Compute pairwise metrics comparing candidate against reference."""
    m = PairwiseMetrics()

    # --- Individual-level ---
    ref_individuals = _get_abox_individuals(reference)
    cand_individuals = _get_abox_individuals(candidate)

    all_classes = set(ref_individuals.keys()) | set(cand_individuals.keys())
    total_ref = 0
    total_cand = 0
    total_matched = 0

    for cls in sorted(all_classes):
        ref_set = ref_individuals.get(cls, set())
        cand_set = cand_individuals.get(cls, set())

        matched = len(ref_set & cand_set)
        # Also count by class type (ignoring naming differences)
        type_matched = min(len(ref_set), len(cand_set))

        p = type_matched / len(cand_set) if cand_set else 0.0
        r = type_matched / len(ref_set) if ref_set else 0.0

        m.individual_detail[cls] = {
            "reference_count": len(ref_set),
            "candidate_count": len(cand_set),
            "precision": round(p, 3),
            "recall": round(r, 3),
            "f1": round(_f1(p, r), 3),
        }

        total_ref += len(ref_set)
        total_cand += len(cand_set)
        total_matched += type_matched

    m.individual_precision = total_matched / total_cand if total_cand else 0.0
    m.individual_recall = total_matched / total_ref if total_ref else 0.0
    m.individual_f1 = _f1(m.individual_precision, m.individual_recall)

    # Missing / extra individuals (by class)
    for cls in all_classes:
        ref_count = len(ref_individuals.get(cls, set()))
        cand_count = len(cand_individuals.get(cls, set()))
        if ref_count > 0 and cand_count == 0:
            m.missing_individuals.append(f"{cls} ({ref_count} missing)")
        elif cand_count > 0 and ref_count == 0:
            m.extra_individuals.append(f"{cls} ({cand_count} extra)")

    # --- Property-level ---
    ref_props = _get_used_properties(reference)
    cand_props = _get_used_properties(candidate)

    common_props = ref_props & cand_props
    m.property_precision = len(common_props) / len(cand_props) if cand_props else 0.0
    m.property_recall = len(common_props) / len(ref_props) if ref_props else 0.0
    m.property_f1 = _f1(m.property_precision, m.property_recall)
    m.missing_properties = sorted(ref_props - cand_props)
    m.extra_properties = sorted(cand_props - ref_props)

    # --- Triple-level ---
    ref_triples = _get_normalized_triples(reference)
    cand_triples = _get_normalized_triples(candidate)

    common_triples = ref_triples & cand_triples
    m.triple_precision = len(common_triples) / len(cand_triples) if cand_triples else 0.0
    m.triple_recall = len(common_triples) / len(ref_triples) if ref_triples else 0.0
    m.triple_f1 = _f1(m.triple_precision, m.triple_recall)

    # --- Literal overlap ---
    ref_literals = _get_literal_values(reference)
    cand_literals = _get_literal_values(candidate)
    common_literals = ref_literals & cand_literals
    m.literal_overlap = (
        len(common_literals) / len(ref_literals) if ref_literals else 0.0
    )

    # --- Aligned triple metric ---
    ap, ar, af1, n_aligned = _compute_aligned_triple_metric(reference, candidate)
    m.aligned_triple_precision = ap
    m.aligned_triple_recall = ar
    m.aligned_triple_f1 = af1
    m.alignment_size = n_aligned

    return m


# ===================================================================
# Class-aware bipartite alignment for triple-level scoring
# ===================================================================

def _individual_classes(g: Graph) -> dict[URIRef, set[URIRef]]:
    """Map ABox individual URIs to their rdf:type set (excluding TBox types)."""
    result: dict[URIRef, set[URIRef]] = defaultdict(set)
    for s, _, o in g.triples((None, RDF.type, None)):
        if not isinstance(s, URIRef):
            continue
        if str(s).startswith(str(AGENTOSCIN)):
            continue
        if isinstance(o, URIRef) and o in TBOX_TYPES:
            continue
        result[s].add(o)
    return dict(result)


def _individual_features(g: Graph, ind: URIRef) -> set[tuple[str, str]]:
    """Feature set for a single individual: (predicate-localname, literal-or-type) pairs.

    Used as the alignment signal: two individuals across graphs are similar
    when they share predicate→literal pairs and predicate→class-of-object pairs.
    """
    feats: set[tuple[str, str]] = set()
    classes = _individual_classes(g)
    for _, p, o in g.triples((ind, None, None)):
        if _is_tbox_triple(ind, p, o):
            continue
        p_name = _local_name(p)
        if isinstance(o, Literal):
            feats.add((p_name, " ".join(str(o).split()).lower()))
        elif isinstance(o, URIRef):
            # use the object's type set rather than its (unstable) name
            o_classes = classes.get(o, set())
            if o_classes:
                for cls in o_classes:
                    feats.add((p_name, "@" + _local_name(cls)))
            else:
                # fall back on local-name (e.g. for fixed schema individuals
                # like agentoscin:Sequential)
                feats.add((p_name, "@" + _local_name(o)))
    # also include declared type(s)
    for cls in classes.get(ind, set()):
        feats.add(("rdf:type", "@" + _local_name(cls)))
    return feats


def _compute_alignment(
    reference: Graph, candidate: Graph
) -> dict[URIRef, URIRef]:
    """Greedy bipartite alignment of candidate→reference individuals, by
    Jaccard of feature sets, restricted to pairs sharing at least one type.
    """
    ref_classes = _individual_classes(reference)
    cand_classes = _individual_classes(candidate)

    # group by class for candidate scoring
    ref_inds = list(ref_classes.keys())
    cand_inds = list(cand_classes.keys())

    ref_feats = {r: _individual_features(reference, r) for r in ref_inds}
    cand_feats = {c: _individual_features(candidate, c) for c in cand_inds}

    # build candidate-pair scores (only when types overlap and features overlap)
    pair_scores: list[tuple[float, URIRef, URIRef]] = []
    for c in cand_inds:
        c_classes = cand_classes[c]
        cf = cand_feats[c]
        if not cf:
            continue
        for r in ref_inds:
            if not (c_classes & ref_classes[r]):
                continue
            rf = ref_feats[r]
            if not rf:
                continue
            inter = len(cf & rf)
            if inter == 0:
                continue
            union = len(cf | rf)
            jacc = inter / union if union else 0.0
            pair_scores.append((jacc, c, r))

    # greedy: highest score first, each individual matched at most once
    pair_scores.sort(key=lambda t: t[0], reverse=True)
    used_c: set[URIRef] = set()
    used_r: set[URIRef] = set()
    alignment: dict[URIRef, URIRef] = {}
    for score, c, r in pair_scores:
        if c in used_c or r in used_r:
            continue
        alignment[c] = r
        used_c.add(c)
        used_r.add(r)
    return alignment


def _compute_aligned_triple_metric(
    reference: Graph, candidate: Graph
) -> tuple[float, float, float, int]:
    """Triple P/R/F1 after rewriting candidate URIs to their aligned reference
    counterparts. Unmatched candidate URIs are kept as-is and therefore will
    not match any reference triple."""
    alignment = _compute_alignment(reference, candidate)

    def rewrite_node(n):
        if isinstance(n, URIRef) and n in alignment:
            return alignment[n]
        return n

    ref_triples = _get_normalized_triples(reference)

    cand_triples: set[tuple[str, str, str]] = set()
    for s, p, o in candidate:
        if _is_tbox_triple(s, p, o):
            continue
        if isinstance(s, URIRef) and str(s).startswith(str(AGENTOSCIN)):
            continue
        s_n = rewrite_node(s)
        o_n = rewrite_node(o)
        s_name = _local_name(s_n) if isinstance(s_n, URIRef) else str(s_n)
        p_name = _local_name(p) if isinstance(p, URIRef) else str(p)
        if isinstance(o_n, Literal):
            o_repr = f'"{str(o_n)}"'
        elif isinstance(o_n, URIRef):
            o_repr = _local_name(o_n)
        else:
            o_repr = str(o_n)
        cand_triples.add((s_name, p_name, o_repr))

    common = ref_triples & cand_triples
    p = len(common) / len(cand_triples) if cand_triples else 0.0
    r = len(common) / len(ref_triples) if ref_triples else 0.0
    return p, r, _f1(p, r), len(alignment)


# ===================================================================
# Report formatting
# ===================================================================

def format_intrinsic_report(m: IntrinsicMetrics, label: str = "Extraction") -> str:
    """Format intrinsic metrics as a human-readable report."""
    lines = [
        f"{'=' * 60}",
        f"INTRINSIC METRICS: {label}",
        f"{'=' * 60}",
        f"  Total triples:        {m.total_triples}",
        f"  ABox triples:         {m.abox_triples}",
        f"  Total individuals:    {m.total_individuals}",
        f"  Properties used:      {m.property_count}",
        f"  Information density:  {m.information_density:.2f} triples/individual",
        f"  Literal values:       {m.literals_count}",
        f"  Object links:         {m.object_links_count}",
        "",
        "  Individuals by class:",
    ]
    for cls, count in m.individual_counts.items():
        lines.append(f"    {cls}: {count}")

    lines.append("")
    lines.append("  Properties exercised:")
    for prop in sorted(m.properties_used):
        lines.append(f"    {prop}")

    return "\n".join(lines)


def format_pairwise_report(m: PairwiseMetrics) -> str:
    """Format pairwise metrics as a human-readable report."""
    lines = [
        f"{'=' * 60}",
        "PAIRWISE COMPARISON METRICS",
        f"{'=' * 60}",
        "",
        "  Individual-level (by class count):",
        f"    Precision: {m.individual_precision:.3f}",
        f"    Recall:    {m.individual_recall:.3f}",
        f"    F1:        {m.individual_f1:.3f}",
        "",
    ]

    if m.individual_detail:
        lines.append("    Per-class breakdown:")
        lines.append(f"    {'Class':<30} {'Ref':>4} {'Cand':>4} {'P':>6} {'R':>6} {'F1':>6}")
        lines.append(f"    {'-' * 56}")
        for cls, detail in sorted(m.individual_detail.items()):
            lines.append(
                f"    {cls:<30} {detail['reference_count']:>4} "
                f"{detail['candidate_count']:>4} "
                f"{detail['precision']:>6.3f} {detail['recall']:>6.3f} "
                f"{detail['f1']:>6.3f}"
            )

    lines.extend([
        "",
        "  Property-level:",
        f"    Precision: {m.property_precision:.3f}",
        f"    Recall:    {m.property_recall:.3f}",
        f"    F1:        {m.property_f1:.3f}",
    ])

    if m.missing_properties:
        lines.append(f"    Missing ({len(m.missing_properties)}):")
        for p in m.missing_properties:
            lines.append(f"      - {p}")
    if m.extra_properties:
        lines.append(f"    Extra ({len(m.extra_properties)}):")
        for p in m.extra_properties:
            lines.append(f"      + {p}")

    lines.extend([
        "",
        "  Triple-level (normalized):",
        f"    Precision: {m.triple_precision:.3f}",
        f"    Recall:    {m.triple_recall:.3f}",
        f"    F1:        {m.triple_f1:.3f}",
        "",
        "  Content fidelity:",
        f"    Literal overlap: {m.literal_overlap:.3f}",
    ])

    if m.missing_individuals:
        lines.append("")
        lines.append("  Missing individual classes:")
        for item in m.missing_individuals:
            lines.append(f"    - {item}")
    if m.extra_individuals:
        lines.append("")
        lines.append("  Extra individual classes:")
        for item in m.extra_individuals:
            lines.append(f"    + {item}")

    return "\n".join(lines)


def format_json_report(
    intrinsic_ref: IntrinsicMetrics | None,
    intrinsic_cand: IntrinsicMetrics | None,
    pairwise: PairwiseMetrics | None,
) -> str:
    """Format all metrics as JSON for programmatic consumption."""
    result: dict = {}

    if intrinsic_ref:
        result["reference"] = {
            "total_triples": intrinsic_ref.total_triples,
            "abox_triples": intrinsic_ref.abox_triples,
            "total_individuals": intrinsic_ref.total_individuals,
            "property_count": intrinsic_ref.property_count,
            "information_density": round(intrinsic_ref.information_density, 3),
            "individual_counts": intrinsic_ref.individual_counts,
        }

    if intrinsic_cand:
        result["candidate"] = {
            "total_triples": intrinsic_cand.total_triples,
            "abox_triples": intrinsic_cand.abox_triples,
            "total_individuals": intrinsic_cand.total_individuals,
            "property_count": intrinsic_cand.property_count,
            "information_density": round(intrinsic_cand.information_density, 3),
            "individual_counts": intrinsic_cand.individual_counts,
        }

    if pairwise:
        result["pairwise"] = {
            "individual": {
                "precision": round(pairwise.individual_precision, 3),
                "recall": round(pairwise.individual_recall, 3),
                "f1": round(pairwise.individual_f1, 3),
                "per_class": pairwise.individual_detail,
            },
            "property": {
                "precision": round(pairwise.property_precision, 3),
                "recall": round(pairwise.property_recall, 3),
                "f1": round(pairwise.property_f1, 3),
                "missing": pairwise.missing_properties,
                "extra": pairwise.extra_properties,
            },
            "triple": {
                "precision": round(pairwise.triple_precision, 3),
                "recall": round(pairwise.triple_recall, 3),
                "f1": round(pairwise.triple_f1, 3),
            },
            "content_fidelity": {
                "literal_overlap": round(pairwise.literal_overlap, 3),
            },
        }

    return json.dumps(result, indent=2)
