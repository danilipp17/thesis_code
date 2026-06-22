"""
fixup_pipeline.py
=================
One-step LLM fixup for generated systems that did not produce their goal.

For every BROKEN cell (generation + cross-framework) we send gpt-5-mini:
  1. the FULL original source of the source framework (code, crews, configs, tools)
  2. the source ontology (.ttl)
  3. a FILE-TREE manifest of the broken generated code   (guard #2)
  4. the broken OSCIN-generated target code
  5. the observed runtime failure
with a prompt that forbids restructuring the file layout / tool imports (guard #1),
and ask it to return corrected target code. We then re-run the corrected system
and record what it produces.

Outputs (for manual verification):
  output/repair/<cell>/broken/         copy of the broken generated tree
  output/repair/<cell>/fixed/          repaired tree (broken + LLM-corrected files)
  output/repair/<cell>/llm_response.txt raw LLM output
  output/repair/<cell>/record.json     before/after outcome + produced snippets
  output/repair/summary.md             one-row-per-cell before/after table
  output/repair/summary.json
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oscin.llm_extractor import call_openai  # noqa: E402
from evaluation.metrics import execution_trace as X  # noqa: E402

MODEL = "gpt-5-mini"
OUT = ROOT / "output" / "repair"
FINDINGS = ROOT / "output" / "runtime_thorough" / "findings.json"
SRC_EXT = {".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".md", ".txt"}

FAMILIES = ["joke", "code-review", "tech-blog",
            "meeting-assistant-flow", "travel-planning", "maths"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]

# Cells that already produced their intended artifact (skip these).
CHECKMARK_GEN = {
    ("joke", "crewai"), ("joke", "autogen"),
    ("code-review", "crewai"), ("code-review", "langgraph"),
    ("tech-blog", "crewai"), ("tech-blog", "langgraph"), ("tech-blog", "autogen"),
    ("travel-planning", "crewai"), ("travel-planning", "langgraph"),
    ("maths", "autogen"),
}
CHECKMARK_CROSS = {
    ("joke", "crewai", "autogen"), ("joke", "langgraph", "autogen"),
    ("tech-blog", "crewai", "autogen"), ("travel-planning", "crewai", "autogen"),
}


def collect_tree(root: Path) -> str:
    parts = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in SRC_EXT:
            continue
        if "__pycache__" in p.parts or p.name.startswith("__"):
            continue
        try:
            parts.append(f"--- {p.relative_to(root)} ---\n{p.read_text(encoding='utf-8')}")
        except Exception:
            continue
    return "\n\n".join(parts)


def manifest(root: Path) -> str:
    files = sorted(str(p.relative_to(root)) for p in root.rglob("*")
                   if p.is_file() and p.suffix in SRC_EXT
                   and "__pycache__" not in p.parts)
    return "\n".join(files)


def failure_signal(rec_key) -> str:
    if not FINDINGS.is_file():
        return "unknown"
    recs = json.loads(FINDINGS.read_text())
    for r in recs:
        if rec_key == _key_of(r):
            return f"outcome={r['outcome']}; error={r.get('error')}; produced={r.get('produced')}"
    return "unknown"


def _key_of(r):
    if r.get("section") == "generation":
        return ("gen", r["family"], r["framework"])
    return ("cross", r["family"], r["src"], r["tgt"])


def build_prompt(src, tgt, original_src, ttl, tree, broken_code, failure) -> str:
    if src == tgt:
        origin = f"A deterministic tool generated this {tgt} code from the ontology below"
    else:
        origin = f"A deterministic tool translated a {src} multi-agent system into {tgt}"
    return f"""You repair auto-generated {tgt} agent code. {origin}, but the generated \
code does not run correctly or does not produce its intended result.

HARD CONSTRAINTS (do not violate):
- Keep the {tgt} framework and the existing file layout EXACTLY. Do not rename, \
move, split, merge, or create files, and do not change the import structure.
- In particular, keep the `tools` module exactly as imported in the broken code \
(e.g. if it does `from tools import add`, keep that — do NOT turn `tools` into a \
package or invent paths like `tools.arithmetic` or `tools/foo.py`).
- Only edit: function/node bodies, agent & prompt wiring (so real inputs are \
interpolated, not left as literal placeholders), state access, and graph/flow edges.
- Make the program run end-to-end on a representative concrete input (like the \
original does) and PRINT the result.

ANTI-CHEATING CONSTRAINTS (critical — a fix that violates these is worthless):
- The result MUST be produced by actually running the {tgt} agent framework at \
run time: real model calls (e.g. model.invoke / team.run_stream / crew.kickoff \
driving the agents) and, where applicable, real tool invocations through the \
framework. The agents/nodes must call the language model.
- Do NOT hardcode, inline, fabricate, simulate, or precompute the answer. There \
must be no literal joke, article, review, itinerary, task list, or numeric result \
written into the source; no "deterministic"/"simulated" stand-in pipelines; no \
bypassing the framework's run loop to compute the answer in plain Python. \
Computing the arithmetic yourself, or writing the joke/article as a string \
literal, is explicitly forbidden.
- The output must be generated by the model at run time, such that two separate \
runs of the program would produce different wording. If your fix would print the \
same bytes every run, it is wrong — make the agents do the work instead.

=== REFERENCE BEHAVIOR — original {src} implementation (all files) ===
{original_src}

=== SEMANTIC SPECIFICATION — ontology the system realises (.ttl) ===
{ttl}

=== FILE TREE OF THE GENERATED CODE (these are the ONLY files; edit in place) ===
{tree}

=== BROKEN GENERATED {tgt} CODE (all files) ===
{broken_code}

=== OBSERVED FAILURE WHEN RUN ===
{failure}

Return ONLY the corrected files, each as:
### FILE: <relative/path exactly as in the file tree>
```python
<full file contents>
```
Repeat for each file you change. No explanations outside the blocks.
"""


FILE_RE = re.compile(r"### FILE:\s*(?P<path>[^\n]+)\n```[a-zA-Z0-9]*\n(?P<body>.*?)```", re.DOTALL)


def parse_files(response: str) -> dict[str, str]:
    out = {}
    for m in FILE_RE.finditer(response):
        out[m.group("path").strip().lstrip("./")] = m.group("body")
    if not out:
        m = re.search(r"```[a-zA-Z0-9]*\n(.*?)```", response, re.DOTALL)
        if m:
            out["main.py"] = m.group(1)
    return out


def run_snip(entry: Path, timeout=90) -> dict:
    r = X.run_target(entry, timeout=timeout)
    out = re.sub(r"\s+", " ", (r.get("stdout") or "").strip())
    return {"ok": bool(r.get("ok")), "duration_s": r.get("duration_s"),
            "error": r.get("error"), "produced": out[:600]}


def fixup(cell: dict) -> dict:
    sec = cell["section"]
    fam = cell["family"]
    if sec == "gen":
        fw = cell["framework"]
        src = tgt = fw
        cell_id = f"gen__{fam}__{fw}"
        src_dir = ROOT / "examples" / "parallel" / fam / fw / "source_files"
        ttl_path = ROOT / "examples" / "parallel" / fam / fw / "ground_truth.ttl"
        broken_dir = ROOT / "output" / "eval_verify" / "generation" / f"{fam}__{fw}" / "generated"
        rec_key = ("gen", fam, fw)
    else:
        src, tgt = cell["src"], cell["tgt"]
        cell_id = f"cross__{fam}__{src}__to__{tgt}"
        src_dir = ROOT / "examples" / "parallel" / fam / src / "source_files"
        ttl_path = ROOT / "examples" / "parallel" / fam / src / "ground_truth.ttl"
        broken_dir = ROOT / "output" / "eval_verify" / "cross" / f"{fam}__{src}__to__{tgt}" / "generated"
        rec_key = ("cross", fam, src, tgt)

    rec = {"cell": cell_id, "section": sec, "family": fam, "src": src, "tgt": tgt}
    if not broken_dir.is_dir():
        rec["status"] = "no_broken_dir"
        print(f"  {cell_id}: no broken dir, skip")
        return rec

    before = failure_signal(rec_key)
    rec["before"] = before
    original_src = collect_tree(src_dir)
    ttl = ttl_path.read_text(encoding="utf-8") if ttl_path.is_file() else ""
    tree = manifest(broken_dir)
    broken_code = collect_tree(broken_dir)

    prompt = build_prompt(src, tgt, original_src, ttl, tree, broken_code, before)
    print(f"  {cell_id}: calling {MODEL} ({len(prompt)} chars)...")
    try:
        resp = call_openai(prompt, model=MODEL)
    except Exception as e:
        rec["status"] = f"llm_error: {e}"
        print(f"    LLM FAILED: {e}")
        return rec

    files = parse_files(resp)
    rec["files_returned"] = list(files.keys())

    cell_out = OUT / cell_id
    cell_out.mkdir(parents=True, exist_ok=True)
    (cell_out / "llm_response.txt").write_text(resp, encoding="utf-8")
    # snapshot broken + build fixed
    for sub in ("broken", "fixed"):
        d = cell_out / sub
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(broken_dir, d)
    if not files:
        rec["status"] = "no_files_parsed"
        print("    could not parse any file")
        return rec
    for rel, body in files.items():
        dst = cell_out / "fixed" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(body, encoding="utf-8")

    entry = cell_out / "fixed" / "main.py"
    if not entry.is_file():
        e2 = X.find_entry(cell_out / "fixed")
        entry = e2 if e2 else entry
    after = run_snip(entry)
    rec["after"] = after
    rec["status"] = "ran_ok" if after["ok"] else "ran_fail"
    print(f"    AFTER: [{'OK' if after['ok'] else 'FAIL'} {after['duration_s']}s "
          f"{after['error'] or ''}] {after['produced'][:160]}")
    return rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cells = []
    for fam in FAMILIES:
        for fw in FRAMEWORKS:
            if (fam, fw) not in CHECKMARK_GEN:
                cells.append({"section": "gen", "family": fam, "framework": fw})
    for fam in FAMILIES:
        for s in FRAMEWORKS:
            for t in FRAMEWORKS:
                if s == t:
                    continue
                if (fam, s, t) not in CHECKMARK_CROSS:
                    cells.append({"section": "cross", "family": fam, "src": s, "tgt": t})

    print(f"Running fixup on {len(cells)} broken cells with {MODEL}\n")
    records = []
    for i, c in enumerate(cells, 1):
        print(f"[{i}/{len(cells)}]")
        records.append(fixup(c))
        (OUT / "summary.json").write_text(json.dumps(records, indent=2))  # incremental

    # markdown summary
    def esc(s): return (s or "").replace("|", "\\|").replace("\n", " ")
    lines = ["# LLM fixup results (gpt-5-mini)", "",
             "| cell | before | after-run | what the fixed system produced |",
             "|---|---|---|---|"]
    for r in records:
        after = r.get("after") or {}
        run = ("OK" if after.get("ok") else "FAIL") if "after" in r else r.get("status", "—")
        prod = esc(after.get("produced", "")) if after else r.get("status", "")
        bef = esc((r.get("before") or "")[:60])
        lines.append(f"| {r['cell']} | {bef} | {run} | {prod[:200]} |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")

    ran_ok = sum(1 for r in records if r.get("status") == "ran_ok")
    print(f"\nDone. {ran_ok}/{len(records)} now run without error. "
          f"See {OUT}/summary.md and per-cell fixed/ dirs.")


if __name__ == "__main__":
    main()
