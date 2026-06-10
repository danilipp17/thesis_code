"""
LLM-baseline extraction across the eighteen-cell parallel corpus.

For each (family, framework) cell:
  1. Run the LLM extractor (OpenAI gpt-4o) on the cell's source tree.
  2. Compare the resulting ABox to the hand-authored ground_truth.ttl
     using the same metric suite the AST extraction experiment uses.
  3. Write per-cell and aggregate results.

Outputs:
  output/llm_baseline_parallel/<family>/<framework>/extracted.ttl
  output/llm_baseline_parallel/summary.json
  output/llm_baseline_parallel/summary.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from statistics import mean

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oscin.llm_extractor import run_llm_extraction  # noqa: E402
from oscin.evaluator import compute_pairwise  # noqa: E402

AO = "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
ONTOLOGY_TTL = ROOT / "ontology" / "agentoscin.ttl"


def _schema_uris() -> set[str]:
    g = Graph()
    g.parse(str(ONTOLOGY_TTL), format="turtle")
    schema = set()
    types = {OWL.Class, RDFS.Class, OWL.ObjectProperty,
             OWL.DatatypeProperty, OWL.AnnotationProperty, RDF.Property}
    for s, _, o in g.triples((None, RDF.type, None)):
        if o in types and isinstance(s, URIRef) and str(s).startswith(AO):
            schema.add(str(s))
    return schema


SCHEMA_URIS = _schema_uris()


def _rebase_graph(g_in: Graph, instance_ns: str) -> Graph:
    """Move non-schema URIs in the AGENTOSCIN namespace to instance_ns."""
    g_out = Graph()
    for prefix, ns in g_in.namespaces():
        g_out.bind(prefix, ns)
    g_out.bind("ex", instance_ns)

    def rewrite(node):
        if isinstance(node, URIRef) and str(node).startswith(AO) and str(node) not in SCHEMA_URIS:
            return URIRef(instance_ns + str(node).replace(AO, ""))
        return node

    for s, p, o in g_in:
        g_out.add((rewrite(s), rewrite(p), rewrite(o)))
    return g_out

FAMILIES = [
    "joke",
    "code-review",
    "tech-blog",
    "meeting-assistant-flow",
    "travel-planning",
    "react",
]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

PROVIDER = "openai"
MODEL = "gpt-4o"
OUT_ROOT = ROOT / "output" / "llm_baseline_parallel"


def _repair_ttl(text: str) -> str:
    # 1. Strip any leading prose before the first @prefix/@base directive.
    m = re.search(r"^@(prefix|base)\b", text, flags=re.MULTILINE)
    if m:
        text = text[m.start():]
    # 2. Inject any of the standard prefixes the LLM forgot.
    prefixes = []
    needed = [
        ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
        ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
        ("xsd", "http://www.w3.org/2001/XMLSchema#"),
        ("owl", "http://www.w3.org/2002/07/owl#"),
        ("dcterms", "http://purl.org/dc/terms/"),
        ("dc", "http://purl.org/dc/elements/1.1/"),
        ("foaf", "http://xmlns.com/foaf/0.1/"),
        ("skos", "http://www.w3.org/2004/02/skos/core#"),
    ]
    for prefix, uri in needed:
        if f"@prefix {prefix}:" not in text:
            prefixes.append(f"@prefix {prefix}: <{uri}> .")
    if prefixes:
        text = "\n".join(prefixes) + "\n" + text
    # 3. Replace ';\n\n<NewSubject>' with '.\n\n<NewSubject>'.
    text = re.sub(r";\s*\n\s*\n(?=[:a-zA-Z_])", ".\n\n", text)
    text = re.sub(r";\s*\n\s*\n###", ".\n\n###", text)
    return text


def load_graph(p: Path) -> Graph | None:
    g = Graph()
    try:
        g.parse(str(p), format="turtle")
        return g
    except Exception:
        try:
            text = Path(p).read_text(encoding="utf-8")
            repaired = _repair_ttl(text)
            g2 = Graph()
            g2.parse(data=repaired, format="turtle")
            print(f"    parse OK after repair for {p.name}")
            return g2
        except Exception as e:
            print(f"    parse FAILED for {p}: {str(e)[:140]}")
            return None


def cell_metrics(gt: Graph, cand: Graph) -> dict:
    m = compute_pairwise(gt, cand)
    return {
        "triple_f1": m.triple_f1,
        "aligned_triple_f1": m.aligned_triple_f1,
        "individual_f1": m.individual_f1,
        "property_f1": m.property_f1,
        "literal_overlap": m.literal_overlap,
    }


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    cells: list[dict] = []

    for family in FAMILIES:
        for fw in FRAMEWORKS:
            cell_id = f"{family}__{fw}"
            print(f"\n=== {cell_id} ===")
            example_root = ROOT / "examples" / "parallel" / family / fw
            source_dir = example_root / "source_files"
            gt_path = example_root / "ground_truth.ttl"

            if not source_dir.is_dir():
                print(f"  skip: source_dir not found ({source_dir})")
                continue
            if not gt_path.is_file():
                print(f"  skip: ground_truth.ttl not found ({gt_path})")
                continue

            out_dir = OUT_ROOT / family / fw
            out_dir.mkdir(parents=True, exist_ok=True)
            llm_ttl = out_dir / "extracted.ttl"

            ns = f"http://example.org/{family.replace('-', '_')}#"

            if not llm_ttl.exists():
                print("  calling LLM...")
                try:
                    run_llm_extraction(
                        source_dir=source_dir,
                        output_path=llm_ttl,
                        instance_namespace=ns,
                        provider=PROVIDER,
                        model=MODEL,
                    )
                except Exception as e:
                    print(f"  LLM call FAILED: {e}")
                    cells.append({
                        "family": family,
                        "framework": fw,
                        "error": f"llm: {e}",
                    })
                    continue
            else:
                print("  llm output cached, skipping call")

            g_gt = load_graph(gt_path)
            g_llm = load_graph(llm_ttl)

            row = {"family": family, "framework": fw}

            if g_gt is None or g_llm is None:
                row["error"] = "parse failed"
                cells.append(row)
                continue

            # Move non-schema URIs in the AGENTOSCIN namespace to the GT
            # instance namespace so triples become comparable.
            g_llm = _rebase_graph(g_llm, ns)

            metrics = cell_metrics(g_gt, g_llm)
            row.update(metrics)
            row["gt_triples"] = sum(1 for _ in g_gt)
            row["llm_triples"] = sum(1 for _ in g_llm)
            cells.append(row)
            print(
                f"  triple F1={metrics['triple_f1']:.3f}  aligned={metrics['aligned_triple_f1']:.3f}  "
                f"ind={metrics['individual_f1']:.3f}  prop={metrics['property_f1']:.3f}  "
                f"lit={metrics['literal_overlap']:.3f}"
            )

    # ---- aggregates ----
    def avg(rows, key):
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return mean(vals) if vals else None

    ok = [c for c in cells if "error" not in c]
    framework_agg = {
        fw: {
            level: avg([c for c in ok if c["framework"] == fw], level)
            for level in (
                "triple_f1",
                "aligned_triple_f1",
                "individual_f1",
                "property_f1",
                "literal_overlap",
            )
        }
        for fw in FRAMEWORKS
    }
    family_agg = {
        fam: {
            level: avg([c for c in ok if c["family"] == fam], level)
            for level in (
                "triple_f1",
                "aligned_triple_f1",
                "individual_f1",
                "property_f1",
                "literal_overlap",
            )
        }
        for fam in FAMILIES
    }
    overall = {
        level: avg(ok, level)
        for level in (
            "triple_f1",
            "aligned_triple_f1",
            "individual_f1",
            "property_f1",
            "literal_overlap",
        )
    }

    summary = {
        "provider": PROVIDER,
        "model": MODEL,
        "cells": cells,
        "overall_mean": overall,
        "framework_mean": framework_agg,
        "family_mean": family_agg,
    }
    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_ROOT / 'summary.json'}")

    # markdown
    lines = ["# LLM baseline (parallel corpus)", ""]
    lines.append(f"Provider: {PROVIDER}  Model: {MODEL}")
    lines.append("")
    lines.append("## Per-cell")
    lines.append("")
    lines.append("| family | framework | triple | aligned | ind | prop | literal | err |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in cells:
        if "error" in c:
            lines.append(f"| {c['family']} | {c['framework']} | — | — | — | — | — | {c['error']} |")
        else:
            lines.append(
                f"| {c['family']} | {c['framework']} | "
                f"{c['triple_f1']:.3f} | {c['aligned_triple_f1']:.3f} | "
                f"{c['individual_f1']:.3f} | {c['property_f1']:.3f} | "
                f"{c['literal_overlap']:.3f} | |"
            )
    lines.append("")
    lines.append("## Aggregates")
    lines.append("")
    lines.append("| group | triple | aligned | ind | prop | literal |")
    lines.append("|---|---|---|---|---|---|")
    def f(v):
        return f"{v:.3f}" if isinstance(v, (int, float)) else "—"

    for fw, m in framework_agg.items():
        lines.append(
            f"| {fw} | {f(m['triple_f1'])} | {f(m['aligned_triple_f1'])} | "
            f"{f(m['individual_f1'])} | {f(m['property_f1'])} | "
            f"{f(m['literal_overlap'])} |"
        )
    for fam, m in family_agg.items():
        lines.append(
            f"| {fam} | {f(m['triple_f1'])} | {f(m['aligned_triple_f1'])} | "
            f"{f(m['individual_f1'])} | {f(m['property_f1'])} | "
            f"{f(m['literal_overlap'])} |"
        )
    lines.append("")
    lines.append(
        f"**Mean** triple={f(overall['triple_f1'])}  "
        f"aligned={f(overall['aligned_triple_f1'])}  "
        f"ind={f(overall['individual_f1'])}  "
        f"prop={f(overall['property_f1'])}  "
        f"lit={f(overall['literal_overlap'])}"
    )
    (OUT_ROOT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT_ROOT / 'summary.md'}")


if __name__ == "__main__":
    main()
