"""
check_determinism.py
====================
Definitive genuine-vs-gamed test for the repaired cells.

A genuinely agentic system calls the model at run time, so its output VARIES
across runs. A 'gamed' repair (hardcoded answer / framework bypass) prints
byte-identical output every run. We run each goal-reached repaired cell TWICE,
normalise away run-specific ids, and compare:

  GENUINE  : the two runs differ  -> the model actually generated the output
  GAMED    : the two runs are identical -> output is hardcoded/deterministic

Output: output/repair/determinism.json / .md
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evaluation.metrics import execution_trace as X  # noqa: E402

REPAIR = ROOT / "output" / "repair"

def normalise(s: str) -> str:
    s = s or ""
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<UUID>", s)
    s = re.sub(r"\b[0-9a-f]{12,}\b", "<HEX>", s)
    s = re.sub(r"call_[A-Za-z0-9]+", "<CALLID>", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()

def run(entry: Path) -> str:
    r = X.run_target(entry, timeout=90)
    return r.get("stdout") or ""

def main():
    v = json.load(open(REPAIR / "verify.json"))
    cells = [r["cell"] for r in v if r["verdict"] in ("CORRECT", "PARTIAL")]
    out = []
    for cell in cells:
        entry = REPAIR / cell / "fixed" / "main.py"
        if not entry.is_file():
            e2 = X.find_entry(REPAIR / cell / "fixed"); entry = e2 or entry
        a = run(entry); b = run(entry)
        na, nb = normalise(a), normalise(b)
        identical = (na == nb)
        verdict = "GAMED" if identical else "GENUINE"
        out.append({"cell": cell, "verdict": verdict,
                    "len1": len(na), "len2": len(nb)})
        print(f"{verdict:8s} {cell:46s} (len {len(na)} vs {len(nb)})")
    (REPAIR / "determinism.json").write_text(json.dumps(out, indent=2))
    from collections import Counter
    c = Counter(r["verdict"] for r in out)
    print(f"\n{dict(c)}  of {len(out)} goal-reached cells")

if __name__ == "__main__":
    main()
