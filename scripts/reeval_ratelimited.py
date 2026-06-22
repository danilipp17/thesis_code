"""
Re-evaluate the rate-limited cells with spacing between runs to avoid 429s,
then merge the corrected verdicts back into final_eval.json.
"""
from __future__ import annotations
import json, time, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.final_eval import evaluate, family_of  # noqa: E402

REPAIR = ROOT / "output" / "repair"
GAP = 25  # seconds between cells to stay under the rate limit


def main():
    cells = json.loads((REPAIR / "_ratelimited.json").read_text())
    final = json.loads((REPAIR / "final_eval.json").read_text())
    by_cell = {r["cell"]: r for r in final}

    for i, cell in enumerate(cells):
        fam = family_of(cell)
        d = REPAIR / cell / "fixed"
        res = evaluate(d, fam)
        # one retry if still rate-limited
        if "ratelimit" in (res.get("detail") or "").lower():
            time.sleep(GAP)
            res = evaluate(d, fam)
        by_cell[cell].update(res)
        print(f"{cell:42s} -> {res['verdict']}  {str(res.get('detail'))[:50]}")
        if i < len(cells) - 1:
            time.sleep(GAP)

    merged = list(by_cell.values())
    (REPAIR / "final_eval.json").write_text(json.dumps(merged, indent=2))

    from collections import Counter
    rep = [r for r in merged if r["group"] == "repair"]
    pre = [r for r in merged if r["group"] == "pre-fixup"]
    print("\n=== PRE-FIXUP ===", dict(Counter(r["verdict"] for r in pre)))
    print("=== REPAIR (corrected) ===", dict(Counter(r["verdict"] for r in rep)))


if __name__ == "__main__":
    main()
