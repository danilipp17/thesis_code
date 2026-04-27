"""
CQ-survivability evaluation.

For each roundtrip system in output/roundtrip_same/<fw>/<example>/, we
parse TTL1 (extraction from original source) and TTL2 (extraction from
regenerated source) and run a small set of SPARQL competency queries
on both. A CQ is reported as "preserved" iff both graphs return the
same answer set (after local-name canonicalisation).

The 4 CQs encoded here (SPARQL versions of the questions in Table 7.2):

  CQ-1  Which agents are defined and what identifies each?
  CQ-10 What coordination pattern does each team follow?
  CQ-14 What is the step-by-step workflow structure (ordered steps)?
  CQ-18 What tools are available and what inputs does each expect?

Output:
    output/cq_survivability/summary.json
    output/cq_survivability/summary.md
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
ROUND = ROOT / "output/roundtrip_same"
OUT = ROOT / "output/cq_survivability"

PREFIX = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ao:   <http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/>
"""

CQS = {
    "CQ-1": (
        "Which agents are defined and how is each identified?",
        PREFIX + """
        SELECT ?agent ?id WHERE {
          ?agent a ao:Agent .
          OPTIONAL { ?agent ao:agentID ?id }
        }
        """,
    ),
    "CQ-10": (
        "What coordination pattern does each team follow?",
        PREFIX + """
        SELECT ?team ?pattern WHERE {
          ?team a ao:Team ;
                ao:employsCoordinationPattern ?pattern .
        }
        """,
    ),
    "CQ-14": (
        "What is the step-by-step workflow structure (ordered steps)?",
        PREFIX + """
        SELECT ?step ?order WHERE {
          ?step ao:stepOrder ?order .
        }
        """,
    ),
    "CQ-18": (
        "What tools are available and what input schema does each expect?",
        PREFIX + """
        SELECT ?tool ?schema WHERE {
          ?tool a ao:Tool .
          OPTIONAL { ?tool ao:hasInputSchema ?schema }
        }
        """,
    ),
}


def _local(node) -> str:
    s = str(node)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s


def _canonical_row(row) -> tuple:
    return tuple(_local(v) if v is not None else None for v in row)


def query_set(g: Graph, sparql: str) -> set[tuple]:
    rows = set()
    for r in g.query(sparql):
        rows.add(_canonical_row(r))
    return rows


def evaluate_pair(ttl1: Path, ttl2: Path) -> dict:
    g1 = Graph(); g1.parse(str(ttl1), format="turtle")
    g2 = Graph(); g2.parse(str(ttl2), format="turtle")
    out = {}
    for cq_id, (_, sparql) in CQS.items():
        a1 = query_set(g1, sparql)
        a2 = query_set(g2, sparql)
        inter = a1 & a2
        union = a1 | a2
        jaccard = (len(inter) / len(union)) if union else 1.0
        out[cq_id] = {
            "n_g1": len(a1),
            "n_g2": len(a2),
            "intersection": len(inter),
            "jaccard": jaccard,
            "preserved_exact": a1 == a2,
        }
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for fw_dir in sorted(ROUND.iterdir()):
        if not fw_dir.is_dir():
            continue
        for ex_dir in sorted(fw_dir.iterdir()):
            ttl1 = ex_dir / "ttl1.ttl"
            ttl2 = ex_dir / "ttl2.ttl"
            if not (ttl1.exists() and ttl2.exists()):
                continue
            try:
                res = evaluate_pair(ttl1, ttl2)
            except Exception as e:
                print(f"  failed {fw_dir.name}/{ex_dir.name}: {e}")
                continue
            rows.append({"framework": fw_dir.name, "example": ex_dir.name, "cqs": res})

    summary_per_cq = defaultdict(lambda: {"preserved": 0, "total": 0, "jaccard_sum": 0.0})
    for row in rows:
        for cq_id, m in row["cqs"].items():
            d = summary_per_cq[cq_id]
            d["total"] += 1
            d["jaccard_sum"] += m["jaccard"]
            if m["preserved_exact"]:
                d["preserved"] += 1

    aggregated = {}
    for cq_id, d in summary_per_cq.items():
        aggregated[cq_id] = {
            "preserved_exact_rate": d["preserved"] / d["total"] if d["total"] else 0.0,
            "mean_jaccard": d["jaccard_sum"] / d["total"] if d["total"] else 0.0,
            "n_systems": d["total"],
        }

    (OUT / "summary.json").write_text(json.dumps({"per_system": rows, "aggregate": aggregated}, indent=2))

    lines = ["# CQ-survivability across same-framework roundtrip", ""]
    lines.append("Compares answer sets for each CQ on TTL1 (G1, original extraction)")
    lines.append("and TTL2 (G2, re-extracted after regenerating source).")
    lines.append("")
    lines.append("## Aggregate (over %d systems)" % len(rows))
    lines.append("")
    lines.append("| CQ | question | preserved-exact rate | mean Jaccard | n |")
    lines.append("|---|---|---|---|---|")
    for cq_id, (q, _) in CQS.items():
        a = aggregated.get(cq_id, {})
        lines.append(
            f"| {cq_id} | {q} | {a.get('preserved_exact_rate', 0):.2f} | "
            f"{a.get('mean_jaccard', 0):.3f} | {a.get('n_systems', 0)} |"
        )

    lines.append("")
    lines.append("## Per-system detail")
    lines.append("")
    lines.append("| framework | example | " + " | ".join(f"{cq} (G1/G2/J)" for cq in CQS) + " |")
    lines.append("|---|---|" + "|".join(["---"] * len(CQS)) + "|")
    for row in rows:
        cells = []
        for cq_id in CQS:
            m = row["cqs"][cq_id]
            cells.append(f"{m['n_g1']}/{m['n_g2']}/{m['jaccard']:.2f}")
        lines.append(f"| {row['framework']} | {row['example']} | " + " | ".join(cells) + " |")

    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT}/summary.{{json,md}}")


if __name__ == "__main__":
    main()
