"""
runtime_thorough.py
===================
Thorough runtime evaluation: actually RUN every generated system (18
generation cells + 36 cross-framework cells) and record what it produces.

For each cell we capture:
  - outcome   : OK_REAL / OK_TRIVIAL / FAIL / TIMEOUT
  - duration  : wall-clock seconds
  - error     : exception type+message if it crashed
  - produced  : a cleaned snippet of what the run actually output
                (the agent's product, or the crash reason)

Output:
  output/runtime_thorough/findings.json   (full captured stdout per cell)
  output/runtime_thorough/generation.md   (18-row findings table)
  output/runtime_thorough/cross.md        (36-row findings table)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.metrics import execution_trace as X  # noqa: E402

FAMILIES = ["joke", "code-review", "tech-blog",
            "meeting-assistant-flow", "travel-planning", "maths"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

GEN_ROOT = ROOT / "output" / "eval_verify" / "generation"
CROSS_ROOT = ROOT / "output" / "eval_verify" / "cross"
OUT = ROOT / "output" / "runtime_thorough"
TIMEOUT = 90.0
TRIVIAL_MAX_DURATION = 2.0
TRIVIAL_MAX_STDOUT = 80

# Lines that are pure framework chrome / boilerplate, not real product.
NOISE = re.compile(
    r"^[\s│╭╮╰╯─=*\-]*$"                       # box drawing / rules
    r"|Flow (Execution|Started|Finished)"
    r"|^\s*(ID|Name|Method|Status|Tool Args|Assigned to):"
    r"|Crew Execution|Task Completion|Agent:"
    r"|^\s*Start the task\.?\s*$"
    r"|LangChainPendingDeprecationWarning|JsonPlusSerializer|allowed_objects",
    re.IGNORECASE,
)


def classify(r: dict) -> str:
    err = (r.get("error") or "").lower()
    if "timeout" in err:
        return "TIMEOUT"
    if not r.get("ok"):
        return "FAIL"
    dur = r.get("duration_s") or 0.0
    out = (r.get("stdout") or "").strip()
    if dur < TRIVIAL_MAX_DURATION and len(out) < TRIVIAL_MAX_STDOUT:
        return "OK_TRIVIAL"
    return "OK_REAL"


def produced_snippet(r: dict, outcome: str, limit: int = 240) -> str:
    """A short human-readable summary of what the run produced."""
    if outcome == "FAIL":
        return "CRASH: " + (r.get("error") or "unknown error")
    if outcome == "TIMEOUT":
        return f"TIMEOUT after {TIMEOUT:.0f}s (likely an unbounded agent loop)"
    out = (r.get("stdout") or "")
    # keep only informative lines
    good = []
    for line in out.splitlines():
        s = line.strip()
        if not s or NOISE.search(s):
            continue
        good.append(s)
    text = " ".join(good).strip()
    text = re.sub(r"\s+", " ", text)
    if outcome == "OK_TRIVIAL" or not text:
        return "ran cleanly but produced no agent output (placeholder/stub nodes)"
    snippet = text[:limit]
    return snippet + ("…" if len(text) > limit else "")


def run_one(entry: Path) -> dict:
    r = X.run_target(entry, timeout=TIMEOUT)
    outcome = classify(r)
    return {
        "outcome": outcome,
        "duration_s": r.get("duration_s"),
        "error": r.get("error"),
        "produced": produced_snippet(r, outcome),
        "stdout_full": (r.get("stdout") or "")[:6000],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []

    # ---- generation (18) ----
    gen_rows = []
    for fam in FAMILIES:
        for fw in FRAMEWORKS:
            entry = GEN_ROOT / f"{fam}__{fw}" / "generated" / "main.py"
            if not entry.is_file():
                e2 = X.find_entry(GEN_ROOT / f"{fam}__{fw}" / "generated")
                entry = e2 if e2 else entry
            rec = {"section": "generation", "family": fam, "framework": fw}
            rec.update(run_one(Path(entry)) if entry and entry.is_file()
                       else {"outcome": "NO_ENTRY", "duration_s": None,
                             "error": "no entry", "produced": "no entry file", "stdout_full": ""})
            records.append(rec)
            gen_rows.append(rec)
            print(f"[gen]  {fam:24s} {fw:10s} {rec['outcome']:11s} {rec['duration_s']}s")

    # ---- cross (36) ----
    cross_rows = []
    for fam in FAMILIES:
        for s in FRAMEWORKS:
            for t in FRAMEWORKS:
                if s == t:
                    continue
                entry = CROSS_ROOT / f"{fam}__{s}__to__{t}" / "generated" / "main.py"
                if not entry.is_file():
                    e2 = X.find_entry(CROSS_ROOT / f"{fam}__{s}__to__{t}" / "generated")
                    entry = e2 if e2 else entry
                rec = {"section": "cross", "family": fam, "src": s, "tgt": t}
                rec.update(run_one(Path(entry)) if entry and entry.is_file()
                           else {"outcome": "NO_ENTRY", "duration_s": None,
                                 "error": "no entry", "produced": "no entry file", "stdout_full": ""})
                records.append(rec)
                cross_rows.append(rec)
                print(f"[cross] {fam:22s} {s}->{t:10s} {rec['outcome']:11s} {rec['duration_s']}s")

    (OUT / "findings.json").write_text(json.dumps(records, indent=2))

    def esc(s: str) -> str:
        return (s or "").replace("|", "\\|").replace("\n", " ")

    # generation table
    g = ["# Runtime findings — generation (18 cells)", "",
         "| family | framework | outcome | dur (s) | what running the system produced |",
         "|---|---|---|---|---|"]
    for r in gen_rows:
        g.append(f"| {r['family']} | {r['framework']} | {r['outcome']} | "
                 f"{r['duration_s']} | {esc(r['produced'])} |")
    (OUT / "generation.md").write_text("\n".join(g) + "\n")

    # cross table
    c = ["# Runtime findings — cross-framework (36 cells)", "",
         "| family | direction | outcome | dur (s) | what running the system produced |",
         "|---|---|---|---|---|"]
    for r in cross_rows:
        c.append(f"| {r['family']} | {r['src']}->{r['tgt']} | {r['outcome']} | "
                 f"{r['duration_s']} | {esc(r['produced'])} |")
    (OUT / "cross.md").write_text("\n".join(c) + "\n")

    def tally(rows):
        from collections import Counter
        return dict(Counter(r["outcome"] for r in rows))
    print("\nGENERATION:", tally(gen_rows))
    print("CROSS:", tally(cross_rows))
    print(f"Wrote {OUT}/findings.json, generation.md, cross.md")


if __name__ == "__main__":
    main()
