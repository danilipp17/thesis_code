"""
Inspect cross-framework comparison: compute pairwise metrics for each cell
under TWO possible reference choices:

  A) reference = source-framework hand-authored GT   (the generator input)
                 → measures round-trip-through-target loss

  B) reference = target-framework hand-authored GT   (interoperability target)
                 → measures whether the translation matches what a human would
                   write for the target framework

For each of the 36 ordered (family, S, T) cells, print both metrics so we can
see which interpretation matches the table numbers already in the thesis.
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

FAMILIES = ["joke", "code-review", "tech-blog", "meeting-assistant-flow",
            "travel-planning", "react"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

CROSS_ROOT = ROOT / "output" / "parallel_eval_v2" / "cross"


def _gt(family: str, fw: str) -> Path:
    return ROOT / "examples" / "parallel" / family / fw / "ground_truth.ttl"


def _reextracted(family: str, src: str, tgt: str) -> Path:
    return CROSS_ROOT / f"{family}__{src}__to__{tgt}" / "reextracted.ttl"


def load(p: Path) -> Graph | None:
    if not p.exists():
        return None
    g = Graph()
    try:
        g.parse(str(p), format="turtle")
        return g
    except Exception as e:
        print(f"  parse failed for {p}: {e}")
        return None


def metrics(ref: Graph, cand: Graph) -> dict:
    m = compute_pairwise(ref, cand)
    return {
        "triple_f1": m.triple_f1,
        "aligned_triple_f1": m.aligned_triple_f1,
        "individual_f1": m.individual_f1,
        "property_f1": m.property_f1,
        "literal_overlap": m.literal_overlap,
    }


def main() -> None:
    rows = []
    for family in FAMILIES:
        for src in FRAMEWORKS:
            for tgt in FRAMEWORKS:
                if src == tgt:
                    continue
                re_path = _reextracted(family, src, tgt)
                gt_src = load(_gt(family, src))
                gt_tgt = load(_gt(family, tgt))
                g_re = load(re_path)
                if not (gt_src and gt_tgt and g_re):
                    rows.append({"family": family, "src": src, "tgt": tgt,
                                 "error": "missing"})
                    continue
                row = {
                    "family": family, "src": src, "tgt": tgt,
                    "A_vs_src_gt": metrics(gt_src, g_re),
                    "B_vs_tgt_gt": metrics(gt_tgt, g_re),
                }
                rows.append(row)

    ok = [r for r in rows if "error" not in r]
    def avg(key, group="A_vs_src_gt"):
        vals = [r[group][key] for r in ok]
        return mean(vals)

    print()
    print("=== Choice A — reference = source-framework GT (round-trip view) ===")
    for k in ("triple_f1", "aligned_triple_f1", "individual_f1",
              "property_f1", "literal_overlap"):
        print(f"  mean {k:18s} = {avg(k, 'A_vs_src_gt'):.3f}")

    print()
    print("=== Choice B — reference = target-framework GT (interop view) ===")
    for k in ("triple_f1", "aligned_triple_f1", "individual_f1",
              "property_f1", "literal_overlap"):
        print(f"  mean {k:18s} = {avg(k, 'B_vs_tgt_gt'):.3f}")

    print()
    print("=== Per-direction means (Choice A | Choice B) ===")
    directions = [(s, t) for s in FRAMEWORKS for t in FRAMEWORKS if s != t]
    for s, t in directions:
        cells = [r for r in ok if r["src"] == s and r["tgt"] == t]
        if not cells:
            continue
        def m(group, key):
            return mean(r[group][key] for r in cells)
        print(
            f"  {s:9s} -> {t:9s}  "
            f"A: triple {m('A_vs_src_gt','triple_f1'):.3f} "
            f"aligned {m('A_vs_src_gt','aligned_triple_f1'):.3f} "
            f"ind {m('A_vs_src_gt','individual_f1'):.3f} | "
            f"B: triple {m('B_vs_tgt_gt','triple_f1'):.3f} "
            f"aligned {m('B_vs_tgt_gt','aligned_triple_f1'):.3f} "
            f"ind {m('B_vs_tgt_gt','individual_f1'):.3f}"
        )

    out = CROSS_ROOT.parent / "crossfw_both_references.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
