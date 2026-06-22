"""
runtime_generation.py
=====================
Live execution test of the generated code for every generation cell.

For each (family, framework) cell, run the generated entry-point in a fresh
subprocess (via execution_trace.run_target) and classify the outcome:

  OK_REAL    - ran to completion AND did substantive work
               (multi-second duration or non-trivial stdout)
  OK_TRIVIAL - exited cleanly but sub-second with little/no output
               (placeholder/stub bodies, no real agent execution)
  FAIL       - raised an exception / non-zero exit at runtime
  TIMEOUT    - exceeded the wall-clock timeout

Writes output/runtime_generation/summary.{json,md}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.metrics import execution_trace as X  # noqa: E402

FAMILIES = ["joke", "code-review", "tech-blog",
            "meeting-assistant-flow", "travel-planning", "maths"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

GEN_ROOT = ROOT / "output" / "eval_verify" / "generation"
OUT = ROOT / "output" / "runtime_generation"
TIMEOUT = 90.0

# Heuristic thresholds for the OK_REAL vs OK_TRIVIAL split.
TRIVIAL_MAX_DURATION = 2.0     # seconds
TRIVIAL_MAX_STDOUT_CHARS = 80  # non-whitespace chars of user stdout


def classify(r: dict) -> str:
    err = r.get("error") or ""
    if "timeout" in err.lower():
        return "TIMEOUT"
    if not r.get("ok"):
        return "FAIL"
    dur = r.get("duration_s") or 0.0
    stdout = (r.get("stdout") or "").strip()
    if dur < TRIVIAL_MAX_DURATION and len(stdout) < TRIVIAL_MAX_STDOUT_CHARS:
        return "OK_TRIVIAL"
    return "OK_REAL"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for fam in FAMILIES:
        for fw in FRAMEWORKS:
            cell = f"{fam}__{fw}"
            entry = GEN_ROOT / cell / "generated" / "main.py"
            if not entry.is_file():
                # fall back to any entry the finder locates
                found = X.find_entry(GEN_ROOT / cell / "generated")
                entry = found if found else entry
            if not entry or not entry.is_file():
                rows.append({"family": fam, "framework": fw,
                             "outcome": "NO_ENTRY", "duration_s": None,
                             "error": "no entry file", "stdout_tail": ""})
                print(f"{cell:34s} NO_ENTRY")
                continue
            r = X.run_target(Path(entry), timeout=TIMEOUT)
            outcome = classify(r)
            stdout_tail = "\n".join((r.get("stdout") or "").strip().splitlines()[-4:])
            rows.append({
                "family": fam, "framework": fw, "outcome": outcome,
                "duration_s": r.get("duration_s"),
                "error": r.get("error"),
                "stdout_tail": stdout_tail,
            })
            print(f"{cell:34s} {outcome:11s} {r.get('duration_s')}s  {r.get('error') or ''}")

    (OUT / "summary.json").write_text(json.dumps(rows, indent=2))

    # ---- aggregate ----
    cats = ["OK_REAL", "OK_TRIVIAL", "FAIL", "TIMEOUT", "NO_ENTRY"]
    def counts(sub):
        return {c: sum(1 for r in sub if r["outcome"] == c) for c in cats}

    lines = ["# Runtime test — generated code (generation experiment)", ""]
    lines.append(f"Timeout per cell: {TIMEOUT}s. n = {len(rows)} cells.")
    lines.append("")
    lines.append("## Per-cell")
    lines.append("")
    lines.append("| family | framework | outcome | duration_s | error |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r['family']} | {r['framework']} | {r['outcome']} | "
                     f"{r['duration_s']} | {r['error'] or ''} |")
    lines.append("")
    lines.append("## By framework")
    lines.append("")
    lines.append("| framework | OK_REAL | OK_TRIVIAL | FAIL | TIMEOUT |")
    lines.append("|---|---|---|---|---|")
    for fw in FRAMEWORKS:
        c = counts([r for r in rows if r["framework"] == fw])
        lines.append(f"| {fw} | {c['OK_REAL']} | {c['OK_TRIVIAL']} | {c['FAIL']} | {c['TIMEOUT']} |")
    c = counts(rows)
    lines.append(f"| **all** | {c['OK_REAL']} | {c['OK_TRIVIAL']} | {c['FAIL']} | {c['TIMEOUT']} |")
    lines.append("")
    runnable = c["OK_REAL"] + c["OK_TRIVIAL"]
    lines.append(f"**Runs without error (OK_REAL+OK_TRIVIAL):** {runnable}/{len(rows)} "
                 f"({runnable/len(rows):.0%})")
    lines.append(f"**Does real work (OK_REAL):** {c['OK_REAL']}/{len(rows)} "
                 f"({c['OK_REAL']/len(rows):.0%})")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"\nWrote {OUT/'summary.json'} and {OUT/'summary.md'}")
    print(f"OK_REAL={c['OK_REAL']} OK_TRIVIAL={c['OK_TRIVIAL']} FAIL={c['FAIL']} TIMEOUT={c['TIMEOUT']}")


if __name__ == "__main__":
    main()
