"""
gt_cross_framework_baseline.py
==============================
For each family, compare the three hand-authored ground-truth ABoxes
against each other pairwise. The result is a natural-divergence
baseline: how different are the same family's GTs across frameworks,
purely because each framework's idiom commits different details?

The cross-framework pipeline numbers can then be read as the gap from
this baseline rather than the gap from a perfect-1.0 ceiling.

Computes both orderings (S vs T and T vs S) because literal overlap is
asymmetric (recall-against-reference).

Output
------
output/gt_baseline/all_pairs.json
output/gt_baseline/summary.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oscin.evaluator import compute_pairwise  # noqa: E402

FAMILIES = ["joke", "code-review", "tech-blog",
            "meeting-assistant-flow", "travel-planning", "maths"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

OUT = ROOT / "output" / "gt_baseline"


def _gt(family: str, fw: str) -> Path:
    return ROOT / "examples" / "parallel" / family / fw / "ground_truth.ttl"


def load(p: Path) -> Graph:
    g = Graph(); g.parse(str(p), format="turtle")
    return g


def cell_metrics(ref: Graph, cand: Graph) -> dict:
    m = compute_pairwise(ref, cand)
    return {
        "triple_f1": m.triple_f1,
        "aligned_triple_f1": m.aligned_triple_f1,
        "individual_f1": m.individual_f1,
        "property_f1": m.property_f1,
        "literal_overlap": m.literal_overlap,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for fam in FAMILIES:
        graphs = {fw: load(_gt(fam, fw)) for fw in FRAMEWORKS}
        for s in FRAMEWORKS:
            for t in FRAMEWORKS:
                if s == t:
                    continue
                m = cell_metrics(graphs[s], graphs[t])
                row = {"family": fam, "src": s, "tgt": t, **m}
                rows.append(row)
                print(
                    f"  {fam:22s} {s:9s} -> {t:9s}  "
                    f"triple={m['triple_f1']:.3f}  aligned={m['aligned_triple_f1']:.3f}  "
                    f"ind={m['individual_f1']:.3f}  prop={m['property_f1']:.3f}  "
                    f"lit={m['literal_overlap']:.3f}"
                )

    (OUT / "all_pairs.json").write_text(json.dumps(rows, indent=2))

    def _mean(group, key):
        vals = [r[key] for r in group]
        return mean(vals) if vals else None

    # Per-direction means (6 directions x 6 families)
    md = ["# GT-vs-GT baseline (same family, different framework)", ""]
    md.append("Reference = hand-authored GT for source framework.")
    md.append("Candidate = hand-authored GT for target framework.")
    md.append("Identity rows (S = T) omitted.")
    md.append("")
    md.append("## Per-direction means (averaged over 6 families)")
    md.append("")
    md.append("| direction | triple | aligned | ind | prop | literal |")
    md.append("|---|---|---|---|---|---|")
    for s in FRAMEWORKS:
        for t in FRAMEWORKS:
            if s == t:
                continue
            sub = [r for r in rows if r["src"] == s and r["tgt"] == t]
            md.append(
                f"| {s} -> {t} | "
                f"{_mean(sub, 'triple_f1'):.3f} | {_mean(sub, 'aligned_triple_f1'):.3f} | "
                f"{_mean(sub, 'individual_f1'):.3f} | {_mean(sub, 'property_f1'):.3f} | "
                f"{_mean(sub, 'literal_overlap'):.3f} |"
            )
    md.append("")
    md.append("## Overall mean across all 36 ordered pairs")
    md.append("")
    md.append("| metric | mean |")
    md.append("|---|---|")
    for k in ("triple_f1", "aligned_triple_f1", "individual_f1",
              "property_f1", "literal_overlap"):
        md.append(f"| {k} | {_mean(rows, k):.3f} |")
    md.append("")
    md.append("## Per-cell")
    md.append("")
    md.append("| family | src -> tgt | triple | aligned | ind | prop | literal |")
    md.append("|---|---|---|---|---|---|---|")
    for r in rows:
        md.append(
            f"| {r['family']} | {r['src']} -> {r['tgt']} | "
            f"{r['triple_f1']:.3f} | {r['aligned_triple_f1']:.3f} | "
            f"{r['individual_f1']:.3f} | {r['property_f1']:.3f} | "
            f"{r['literal_overlap']:.3f} |"
        )
    (OUT / "summary.md").write_text("\n".join(md) + "\n")
    print(f"\nWrote {OUT/'all_pairs.json'} and {OUT/'summary.md'}")


if __name__ == "__main__":
    main()
