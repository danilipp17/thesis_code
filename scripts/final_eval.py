"""
final_eval.py
=============
Trustworthy final runtime verdict for every cell, combining a goal check with a
genuineness (non-determinism) check. A cell only counts as a real success if it
(a) produces the intended artifact AND (b) varies across two runs (i.e. the
agents actually call the model, rather than the output being hardcoded).

Per cell we run the entry point TWICE and assign:
  GENUINE   : produces the goal AND the two runs differ        (real success)
  GAMED     : produces goal-like output BUT two runs identical  (hardcoded/bypass)
  NO-GOAL   : runs (and varies) but does not produce the goal
  ERROR     : a run crashes / times out

Scope: the 14 pre-fixup goal-reached cells (deterministic-pipeline output) and
the repaired cells (output/repair/<cell>/fixed). Writes output/repair/final_eval.{json,md}.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evaluation.metrics import execution_trace as X  # noqa: E402

REPAIR = ROOT / "output" / "repair"
EVAL = ROOT / "output" / "eval_verify"

# pre-fixup goal-reached cells (deterministic pipeline; not LLM-repaired)
PRE_GEN = [("joke","crewai"),("joke","autogen"),("code-review","crewai"),
           ("code-review","langgraph"),("tech-blog","crewai"),("tech-blog","langgraph"),
           ("tech-blog","autogen"),("travel-planning","crewai"),
           ("travel-planning","langgraph"),("maths","autogen")]
PRE_CROSS = [("joke","crewai","autogen"),("joke","langgraph","autogen"),
             ("tech-blog","crewai","autogen"),("travel-planning","crewai","autogen")]

FAMILIES = ["joke","code-review","tech-blog","meeting-assistant-flow","travel-planning","maths"]
FRAMEWORKS = ["crewai","langgraph","autogen"]


def family_of(cell: str) -> str:
    for fam in ["code-review","tech-blog","meeting-assistant-flow","travel-planning","joke","maths"]:
        if fam in cell:
            return fam
    return "?"


def goal_met(fam: str, out: str) -> bool:
    low = out.lower(); n = len(out.strip())
    if fam == "maths":          return "312" in out
    if fam == "code-review":    return bool(re.search(r"eval|inject|hard-?coded|cwe|sql|vulnerab|security|owasp", low))
    if fam == "joke":           return "?" in out and n > 40
    if fam == "tech-blog":      return n > 400 and bool(re.search(r"ai|blockchain|quantum|technolog|framework", low))
    if fam == "meeting-assistant-flow":
        return bool(re.search(r"task", low)) and not bool(re.search(r"wrote 0 task|0 new task|\"tasks\"\s*:\s*\[\s*\]", low))
    if fam == "travel-planning":return n > 300 and bool(re.search(r"day|itinerary|visit|morning|plan|trail|tour", low))
    return n > 200


def normalise(s: str) -> str:
    s = s or ""
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<U>", s)
    s = re.sub(r"\b[0-9a-f]{10,}\b", "<H>", s)
    s = re.sub(r"call_[A-Za-z0-9]+", "<C>", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def evaluate(code_dir: Path, fam: str) -> dict:
    entry = code_dir / "main.py"
    if not entry.is_file():
        e2 = X.find_entry(code_dir); entry = e2 or entry
    r1 = X.run_target(entry, timeout=90)
    if not r1.get("ok"):
        return {"verdict": "ERROR", "detail": r1.get("error"), "varies": None, "goal": False}
    r2 = X.run_target(entry, timeout=90)
    o1, o2 = r1.get("stdout") or "", r2.get("stdout") or ""
    varies = normalise(o1) != normalise(o2)
    g = goal_met(fam, o1) or goal_met(fam, o2)
    if not g:
        return {"verdict": "NO-GOAL", "detail": "runs but goal not produced", "varies": varies, "goal": False}
    verdict = "GENUINE" if varies else "GAMED"
    return {"verdict": verdict, "detail": "varies across runs" if varies else "identical across runs (hardcoded)",
            "varies": varies, "goal": True}


def main():
    rows = []

    # pre-fixup cells (deterministic pipeline)
    for fam, fw in PRE_GEN:
        d = EVAL / "generation" / f"{fam}__{fw}" / "generated"
        rows.append({"group": "pre-fixup", "cell": f"gen {fam}/{fw}", **evaluate(d, fam)})
        print(f"[pre]  {rows[-1]['cell']:34s} {rows[-1]['verdict']}")
    for fam, s, t in PRE_CROSS:
        d = EVAL / "cross" / f"{fam}__{s}__to__{t}" / "generated"
        rows.append({"group": "pre-fixup", "cell": f"cross {fam} {s}->{t}", **evaluate(d, fam)})
        print(f"[pre]  {rows[-1]['cell']:34s} {rows[-1]['verdict']}")

    # repaired cells (read which were attempted from summary.json)
    summ = json.loads((REPAIR / "summary.json").read_text())
    for r in summ:
        cell = r["cell"]; fam = family_of(cell)
        d = REPAIR / cell / "fixed"
        if not d.is_dir():
            rows.append({"group": "repair", "cell": cell, "verdict": "ERROR", "detail": "no fixed dir", "varies": None, "goal": False})
            continue
        rows.append({"group": "repair", "cell": cell, **evaluate(d, fam)})
        print(f"[fix]  {cell:40s} {rows[-1]['verdict']}  {rows[-1]['detail']}")

    (REPAIR / "final_eval.json").write_text(json.dumps(rows, indent=2))

    from collections import Counter
    pre = [r for r in rows if r["group"] == "pre-fixup"]
    rep = [r for r in rows if r["group"] == "repair"]
    print("\n=== PRE-FIXUP (deterministic pipeline) ===", dict(Counter(r["verdict"] for r in pre)))
    print("=== REPAIR (hardened prompt) ===", dict(Counter(r["verdict"] for r in rep)))

    md = ["# Final runtime verdict (goal + genuineness)", "",
          "GENUINE = produces goal AND varies across runs; GAMED = goal-like but identical (hardcoded);",
          "NO-GOAL = runs but no goal; ERROR = crash/timeout.", "",
          "| group | cell | verdict | detail |", "|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['group']} | {r['cell']} | {r['verdict']} | {r.get('detail') or ''} |")
    (REPAIR / "final_eval.md").write_text("\n".join(md) + "\n")
    print(f"\nWrote {REPAIR}/final_eval.json and final_eval.md")


if __name__ == "__main__":
    main()
