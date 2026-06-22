"""
verify_fixups.py
================
Re-run every repaired cell that previously 'ran_ok' and capture the FULL output,
then apply a per-family correctness check so we can judge whether the system
actually produced its intended goal (not just executed).

Correctness heuristics (per family):
  maths        -> must contain '312'  ((40+12)*6, deterministic)
  code-review  -> must mention a real finding (eval / injection / hardcoded / CWE / security / vuln)
  joke         -> contains a question-style joke line (>=1 '?') and >40 chars of content
  tech-blog    -> >=400 chars of article text mentioning the topic domain
  meeting      -> mentions task(s) / produces a task list or JSON
  travel       -> itinerary signals (day / visit / plan / morning ...) and >300 chars

Output: output/repair/verify.md  (full captured output per cell + verdict)
        output/repair/verify.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.metrics import execution_trace as X  # noqa: E402

REPAIR = ROOT / "output" / "repair"


def family_of(cell: str) -> str:
    for fam in ["code-review", "tech-blog", "meeting-assistant-flow",
                "travel-planning", "joke", "maths"]:
        if fam in cell:
            return fam
    return "?"


def check(fam: str, out: str) -> tuple[str, str]:
    """Return (verdict, reason). verdict in CORRECT / PARTIAL / NO."""
    low = out.lower()
    n = len(out.strip())
    if fam == "maths":
        if "312" in out:
            return "CORRECT", "computed 312"
        if re.search(r"\b52\b", out):
            return "PARTIAL", "got 52 (add) but no final 312"
        return "NO", "no numeric result"
    if fam == "code-review":
        if re.search(r"eval|inject|hard-?coded|cwe|sql|vulnerab|security|owasp", low):
            return "CORRECT", "names a real finding"
        return "PARTIAL" if n > 200 else "NO", "review text but no clear finding"
    if fam == "joke":
        if "?" in out and n > 40 and "sample" not in low and "start the task" not in low.split("===")[0]:
            return "CORRECT", "joke text present"
        return "PARTIAL", "ran but joke unclear"
    if fam == "tech-blog":
        if n > 400 and re.search(r"ai|blockchain|quantum|technolog|framework", low):
            return "CORRECT", f"{n} chars of article"
        return "PARTIAL", f"only {n} chars"
    if fam == "meeting-assistant-flow":
        if re.search(r"task", low) and (re.search(r"\bjson\b|follow up|description|- ", low)):
            if re.search(r"wrote 0 task|0 new task|\"tasks\"\s*:\s*\[\s*\]", low):
                return "PARTIAL", "pipeline ran but 0 tasks extracted"
            return "CORRECT", "extracted task(s)"
        return "PARTIAL", "ran but no task list"
    if fam == "travel-planning":
        if n > 300 and re.search(r"day|itinerary|visit|morning|plan|trail|tour", low):
            return "CORRECT", f"{n} chars of itinerary"
        return "PARTIAL", f"only {n} chars"
    return "PARTIAL", "no check"


def main() -> None:
    recs = json.loads((REPAIR / "summary.json").read_text())
    ok = [r for r in recs if r.get("status") == "ran_ok"]
    print(f"Re-running {len(ok)} repaired cells for verification\n")

    out_recs = []
    md = ["# Fixup verification — full output + correctness check", ""]
    for r in ok:
        cell = r["cell"]
        fam = family_of(cell)
        entry = REPAIR / cell / "fixed" / "main.py"
        if not entry.is_file():
            e2 = X.find_entry(REPAIR / cell / "fixed")
            entry = e2 if e2 else entry
        res = X.run_target(entry, timeout=90)
        full = (res.get("stdout") or "").strip()
        if not res.get("ok"):
            verdict, reason = "NO", f"crashed: {res.get('error')}"
        else:
            verdict, reason = check(fam, full)
        out_recs.append({"cell": cell, "family": fam, "verdict": verdict,
                         "reason": reason, "ok": bool(res.get("ok")),
                         "duration_s": res.get("duration_s"), "output": full[:4000]})
        print(f"{verdict:8s} {cell:46s} {reason}")
        md.append(f"## {cell}  —  **{verdict}** ({reason})")
        md.append("```")
        md.append(full[:2500] if full else "(no output)")
        md.append("```")
        md.append("")

    (REPAIR / "verify.json").write_text(json.dumps(out_recs, indent=2))
    (REPAIR / "verify.md").write_text("\n".join(md) + "\n")

    from collections import Counter
    c = Counter(r["verdict"] for r in out_recs)
    print(f"\nVERDICTS: {dict(c)}")
    print(f"Wrote {REPAIR}/verify.md (full outputs) and verify.json")


if __name__ == "__main__":
    main()
