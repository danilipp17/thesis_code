"""
Gold-anchored extraction evaluation.

For each of the 6 systems in the evaluation subset, compare:
  - deterministic AST extraction (output/extraction/<fw>/<sys>/extracted.ttl)
  - LLM extraction (output/llm_baseline/run1/<fw>/<sys>/extracted.ttl)
to the hand-authored gold A-Box (output/gold/<fw>/<sys>/gold.ttl).

If an LLM extraction is missing, run it (provider=openai, model=gpt-4o).
LLM TTL is rebased so non-schema URIs in the AGENTOSCIN namespace move to
an instance namespace (same logic as scripts/rebase_llm_ttl.py).

Outputs:
  output/gold_eval/summary.json
  output/gold_eval/summary.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oscin.evaluator import compute_pairwise, compute_intrinsic
from oscin.llm_extractor import run_llm_extraction

EXAMPLES = [
    ("crewai", "email-flow", ROOT / "examples/crewai/email-flow/source_files"),
    ("crewai", "academic-research-flow", ROOT / "examples/crewai/academic-research-flow/source_files"),
    ("langgraph", "ReAct", ROOT / "examples/langgraph/ReAct"),
    ("langgraph", "research-assistant", ROOT / "examples/langgraph/research-assistant/source_files"),
    ("autogen", "code-review", ROOT / "examples/autogen/code-review/source_files"),
    ("autogen", "content-pipeline", ROOT / "examples/autogen/content-pipeline/source_files"),
]

AO = "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
INSTANCE_NS = "http://oscin.example.org/llm-instance#"
PROVIDER = "openai"
MODEL = "gpt-4o"

OUT_ROOT = ROOT / "output/gold_eval"
LLM_ROOT = ROOT / "output/llm_baseline/run1"
DET_ROOT = ROOT / "output/extraction"
GOLD_ROOT = ROOT / "output/gold"


def schema_uris(ontology_ttl: Path) -> set[str]:
    g = Graph()
    g.parse(str(ontology_ttl), format="turtle")
    schema = set()
    schema_types = {OWL.Class, RDFS.Class, OWL.ObjectProperty,
                    OWL.DatatypeProperty, OWL.AnnotationProperty,
                    RDF.Property}
    for s, p, o in g.triples((None, RDF.type, None)):
        if o in schema_types and isinstance(s, URIRef) and str(s).startswith(AO):
            schema.add(str(s))
    return schema


def rebase_graph(g_in: Graph, schema: set[str]) -> Graph:
    g_out = Graph()
    for prefix, ns in g_in.namespaces():
        g_out.bind(prefix, ns)
    g_out.bind("inst", INSTANCE_NS)

    def rewrite(node):
        if isinstance(node, URIRef) and str(node).startswith(AO) and str(node) not in schema:
            return URIRef(INSTANCE_NS + str(node).replace(AO, ""))
        return node

    for s, p, o in g_in:
        g_out.add((rewrite(s), rewrite(p), rewrite(o)))
    return g_out


def parse_ttl_with_repair(path: Path) -> Graph | None:
    """Parse TTL with auto-repairs for common LLM mistakes."""
    original = path.read_text(encoding="utf-8")

    def try_(t: str) -> Graph | None:
        try:
            g = Graph(); g.parse(data=t, format="turtle")
            return g
        except Exception:
            return None

    # Pass 0: as-is
    g = try_(original)
    if g is not None:
        return g

    # Pass 1: inject standard prefixes
    text = original
    std = []
    if "@prefix rdf:" not in text:
        std.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    if "@prefix rdfs:" not in text:
        std.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    if "@prefix xsd:" not in text:
        std.append("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
    if "@prefix owl:" not in text:
        std.append("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    if std:
        text = "\n".join(std) + "\n" + text
        g = try_(text)
        if g is not None:
            return g

    # Pass 2: ';\n\n<subject>' -> '.\n\n<subject>'
    t = re.sub(r";\s*\n\s*\n(?=[:a-zA-Z_])", ".\n\n", text)
    t = re.sub(r";\s*\n\s*\n###", ".\n\n###", t)
    g = try_(t)
    if g is not None:
        return g
    text = t

    # Pass 3: literal-ending line missing terminator before new subject
    # Pattern: "..." followed by newline then a new subject token (':' or '###' or 'a-z')
    # Add a terminating ' .' after the closing quote.
    t = re.sub(r'(\"[^\"\n]*\")\s*\n(\s*)(?=(:|###|[a-zA-Z_]))', r'\1 .\n\2', text)
    g = try_(t)
    if g is not None:
        return g

    return None


def pair_metrics(ref: Graph, cand: Graph) -> dict:
    m = compute_pairwise(ref, cand)
    return {
        "individual_p": round(m.individual_precision, 3),
        "individual_r": round(m.individual_recall, 3),
        "individual_f1": round(m.individual_f1, 3),
        "property_p": round(m.property_precision, 3),
        "property_r": round(m.property_recall, 3),
        "property_f1": round(m.property_f1, 3),
        "triple_p": round(m.triple_precision, 3),
        "triple_r": round(m.triple_recall, 3),
        "triple_f1": round(m.triple_f1, 3),
        "aligned_triple_p": round(m.aligned_triple_precision, 3),
        "aligned_triple_r": round(m.aligned_triple_recall, 3),
        "aligned_triple_f1": round(m.aligned_triple_f1, 3),
        "alignment_size": m.alignment_size,
        "literal_overlap": round(m.literal_overlap, 3),
    }


def intrinsic(g: Graph) -> dict:
    m = compute_intrinsic(g)
    return {
        "abox_triples": m.abox_triples,
        "individuals": m.total_individuals,
        "properties": m.property_count,
    }


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    schema = schema_uris(ROOT / "ontology/agentoscin.ttl")

    summary = {"provider": PROVIDER, "model": MODEL, "examples": []}

    for fw, ex, src in EXAMPLES:
        print(f"\n=== {fw}/{ex} ===")

        gold_ttl = GOLD_ROOT / fw / ex / "gold.ttl"
        det_ttl = DET_ROOT / fw / ex / "extracted.ttl"
        llm_ttl = LLM_ROOT / fw / ex / "extracted.ttl"

        # Run LLM if missing
        if not llm_ttl.exists():
            print(f"  LLM extraction missing → running...")
            try:
                run_llm_extraction(
                    source_dir=src,
                    output_path=llm_ttl,
                    instance_namespace=f"http://oscin.example.org/{fw}/{ex}#",
                    provider=PROVIDER,
                    model=MODEL,
                )
            except Exception as e:
                print(f"  LLM extraction failed: {e}")
                continue

        # Load all 3 graphs
        g_gold = Graph(); g_gold.parse(str(gold_ttl), format="turtle")
        g_det = Graph(); g_det.parse(str(det_ttl), format="turtle")
        g_llm_raw = parse_ttl_with_repair(llm_ttl)
        if g_llm_raw is None:
            print(f"  LLM TTL unparseable, skipping LLM metrics")
            g_llm = None
        else:
            g_llm = rebase_graph(g_llm_raw, schema)
            (llm_ttl.parent / "extracted_rebased.ttl").write_text(
                g_llm.serialize(format="turtle"), encoding="utf-8"
            )

        row = {
            "framework": fw,
            "example": ex,
            "gold_intrinsic": intrinsic(g_gold),
            "det_intrinsic": intrinsic(g_det),
            "det_vs_gold": pair_metrics(g_gold, g_det),
        }
        if g_llm is not None:
            row["llm_intrinsic"] = intrinsic(g_llm)
            row["llm_vs_gold"] = pair_metrics(g_gold, g_llm)
        summary["examples"].append(row)

        print(f"  gold: {row['gold_intrinsic']}")
        d = row["det_vs_gold"]
        print(f"  det:  {row['det_intrinsic']}  ind F1={d['individual_f1']}  prop F1={d['property_f1']}  triple F1={d['triple_f1']}  aligned F1={d['aligned_triple_f1']}")
        if g_llm is not None:
            l = row["llm_vs_gold"]
            print(f"  llm:  {row['llm_intrinsic']}  ind F1={l['individual_f1']}  prop F1={l['property_f1']}  triple F1={l['triple_f1']}  aligned F1={l['aligned_triple_f1']}")

    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_ROOT / 'summary.json'}")

    # Markdown
    lines = ["# Gold-anchored extraction evaluation", ""]
    lines.append(f"Provider={PROVIDER}, model={MODEL}. Gold = hand-authored A-Box.")
    lines.append("")
    lines.append("## Per-system metrics")
    lines.append("")
    lines.append("| framework | example | source | indiv. | abox | prop. | ind F1 | prop F1 | triple F1 | aligned F1 | lit. overlap |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in summary["examples"]:
        gi = r["gold_intrinsic"]
        di = r["det_intrinsic"]
        d = r["det_vs_gold"]
        lines.append(
            f"| {r['framework']} | {r['example']} | gold | {gi['individuals']} | {gi['abox_triples']} | {gi['properties']} | — | — | — | — | — |"
        )
        lines.append(
            f"| {r['framework']} | {r['example']} | deterministic | {di['individuals']} | {di['abox_triples']} | {di['properties']} | {d['individual_f1']} | {d['property_f1']} | {d['triple_f1']} | {d['aligned_triple_f1']} | {d['literal_overlap']} |"
        )
        if "llm_vs_gold" in r:
            li = r["llm_intrinsic"]
            l = r["llm_vs_gold"]
            lines.append(
                f"| {r['framework']} | {r['example']} | LLM (gpt-4o) | {li['individuals']} | {li['abox_triples']} | {li['properties']} | {l['individual_f1']} | {l['property_f1']} | {l['triple_f1']} | {l['aligned_triple_f1']} | {l['literal_overlap']} |"
            )
    lines.append("")
    lines.append("## Aggregate (mean across 6 systems)")
    lines.append("")
    def avg(rows, key):
        vals = [r[key] for r in rows]
        return sum(vals) / len(vals) if vals else 0.0
    det_rows = [r["det_vs_gold"] for r in summary["examples"]]
    llm_rows = [r["llm_vs_gold"] for r in summary["examples"] if "llm_vs_gold" in r]
    lines.append("| source | ind F1 | prop F1 | triple F1 (exact) | triple F1 (aligned) | literal overlap |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(f"| deterministic | {avg(det_rows,'individual_f1'):.3f} | {avg(det_rows,'property_f1'):.3f} | {avg(det_rows,'triple_f1'):.3f} | {avg(det_rows,'aligned_triple_f1'):.3f} | {avg(det_rows,'literal_overlap'):.3f} |")
    if llm_rows:
        lines.append(f"| LLM (gpt-4o, N={len(llm_rows)}) | {avg(llm_rows,'individual_f1'):.3f} | {avg(llm_rows,'property_f1'):.3f} | {avg(llm_rows,'triple_f1'):.3f} | {avg(llm_rows,'aligned_triple_f1'):.3f} | {avg(llm_rows,'literal_overlap'):.3f} |")

    (OUT_ROOT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT_ROOT / 'summary.md'}")


if __name__ == "__main__":
    main()
