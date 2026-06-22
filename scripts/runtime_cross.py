"""
runtime_cross.py
================
Live execution test of the generated TARGET-framework code for every
cross-framework translation cell (family x sourceframework -> targetframework).

Same classification as runtime_generation.py:
  OK_REAL / OK_TRIVIAL / FAIL / TIMEOUT / NO_ENTRY

Writes output/runtime_cross/summary.{json,md}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.metrics import execution_trace as X  # noqa: E402

FAMILIES = ["joke", "code-review", "tech-blog",
            "meeting-assistant-flow", "travel-planning", "maths"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

CROSS_ROOT = ROOT / "output" / "eval_verify" / "cross"
OUT = ROOT / "output" / "runtime_cross"
TIMEOUT = 90.0
TRIVIAL_MAX_DURATION = 2.0
TRIVIAL_MAX_STDOUT_CHARS = 80


def classify(r: dict) -> str:
    err = (r.get("error") or "").lower()
    if "timeout" in err:
        return "TIMEOUT"
    if not r.get("ok"):
        return "FAIL"
    dur = r.get("duration_s") or 0.0
    out = (r.get("stdout") or "").strip()
    if dur < TRIVIAL_MAX_DURATION and len(out) < TRIVIAL_MAX_STDOUT_CHARS:
        return "OK_TRIVIAL"
    return "OK_REAL"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for fam in FAMILIES:
        for src in FRAMEWORKS:
            for tgt in FRAMEWORKS:
                if src == tgt:
                    continue
                cell = f"{fam}__{src}__to__{tgt}"
                entry = CROSS_ROOT / cell / "generated" / "main.py"
                if not entry.is_file():
                    found = X.find_entry(CROSS_ROOT / cell / "generated")
                    entry = found if found else entry
                if not entry or not entry.is_file():
                    rows.append({"family": fam, "src": src, "tgt": tgt,
                                 "outcome": "NO_ENTRY", "duration_s": None,
                                 "error": "no entry file"})
                    print(f"{cell:42s} NO_ENTRY")
                    continue
                r = X.run_target(Path(entry), timeout=TIMEOUT)
                outcome = classify(r)
                rows.append({"family": fam, "src": src, "tgt": tgt,
                             "outcome": outcome, "duration_s": r.get("duration_s"),
                             "error": r.get("error")})
                print(f"{cell:42s} {outcome:11s} {r.get('duration_s')}s  {r.get('error') or ''}")

    (OUT / "summary.json").write_text(json.dumps(rows, indent=2))

    cats = ["OK_REAL", "OK_TRIVIAL", "FAIL", "TIMEOUT", "NO_ENTRY"]
    def counts(sub):
        return {c: sum(1 for r in sub if r["outcome"] == c) for c in cats}

    lines = ["# Runtime test — cross-framework generated target code", ""]
    lines.append(f"Timeout per cell: {TIMEOUT}s. n = {len(rows)} cells.")
    lines.append("")
    lines.append("## Per-cell")
    lines.append("")
    lines.append("| family | direction | outcome | duration_s | error |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r['family']} | {r['src']}->{r['tgt']} | {r['outcome']} | "
                     f"{r['duration_s']} | {r.get('error') or ''} |")
    lines.append("")
    lines.append("## By target framework")
    lines.append("")
    lines.append("| target | OK_REAL | OK_TRIVIAL | FAIL | TIMEOUT |")
    lines.append("|---|---|---|---|---|")
    for tgt in FRAMEWORKS:
        c = counts([r for r in rows if r["tgt"] == tgt])
        lines.append(f"| ->{tgt} | {c['OK_REAL']} | {c['OK_TRIVIAL']} | {c['FAIL']} | {c['TIMEOUT']} |")
    lines.append("")
    lines.append("## By direction")
    lines.append("")
    lines.append("| direction | OK_REAL | OK_TRIVIAL | FAIL | TIMEOUT |")
    lines.append("|---|---|---|---|---|")
    for src in FRAMEWORKS:
        for tgt in FRAMEWORKS:
            if src == tgt:
                continue
            c = counts([r for r in rows if r["src"] == src and r["tgt"] == tgt])
            lines.append(f"| {src}->{tgt} | {c['OK_REAL']} | {c['OK_TRIVIAL']} | {c['FAIL']} | {c['TIMEOUT']} |")
    c = counts(rows)
    lines.append("")
    lines.append(f"| **all** | {c['OK_REAL']} | {c['OK_TRIVIAL']} | {c['FAIL']} | {c['TIMEOUT']} |")
    lines.append("")
    runnable = c["OK_REAL"] + c["OK_TRIVIAL"]
    lines.append(f"**Runs without error:** {runnable}/{len(rows)} ({runnable/len(rows):.0%})")
    lines.append(f"**Does real work (OK_REAL):** {c['OK_REAL']}/{len(rows)} ({c['OK_REAL']/len(rows):.0%})")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print(f"\nWrote {OUT/'summary.json'} and {OUT/'summary.md'}")
    print(f"OK_REAL={c['OK_REAL']} OK_TRIVIAL={c['OK_TRIVIAL']} FAIL={c['FAIL']} TIMEOUT={c['TIMEOUT']}")


if __name__ == "__main__":
    main()
