"""
fixup_framework_agnostic.py
===========================
LLM last-mile repair for the framework-agnostic generations.

For each generated cell (3 systems x 3 frameworks) we send gpt-5-mini:
  1. the framework-agnostic ontology (.ttl) as the semantic spec
  2. the file-tree manifest of the generated code
  3. the full generated (scaffold) code
and ask it to make the program actually run end-to-end and produce its
intended result, by:
  - filling tool bodies with realistic implementations (mock/synthetic
    data where there is no real backend; real logic for things like a
    calculator) -- WITHOUT hardcoding the final answer,
  - fixing framework wiring (LangGraph node state-keys + replacing
    subgraph TODO stubs with real model-invoking nodes; CrewAI Flow step
    bodies + state passing),
  - baking in one concrete representative input.

We then re-run each fixed program TWICE and record whether it produces a
genuine, model-generated result (goal met AND output varies across runs).

Outputs (for manual verification):
  output/framework_agnostic_fix/<cell>/fixed/        repaired tree
  output/framework_agnostic_fix/<cell>/llm_response.txt
  output/framework_agnostic_fix/results.json / results.md
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
GEN = ROOT / "output" / "framework_agnostic_gen"
OUT = ROOT / "output" / "framework_agnostic_fix"
TTL = lambda s: ROOT / "examples" / "framework_agnostic" / s / "ground_truth.ttl"

SYSTEMS = ["incident-commander", "socratic-tutor", "debate-arena"]
FRAMEWORKS = ["crewai", "langgraph", "autogen"]
SRC_EXT = {".py", ".yaml", ".yml", ".json", ".toml", ".txt", ".md"}

# Per-system goal check (substring/length heuristics over stdout).
GOAL = {
    "debate-arena": lambda o: len(o.strip()) > 200 and bool(
        re.search(r"winner|verdict|proponent|opponent|motion", o, re.I)
    ),
    "socratic-tutor": lambda o: len(o.strip()) > 120 and bool(
        re.search(r"answer|step|because|let'?s|consider|\d", o, re.I)
    ),
    "incident-commander": lambda o: len(o.strip()) > 150 and bool(
        re.search(r"root cause|restart|scale|rollback|remediat|incident|service", o, re.I)
    ),
}


def collect_tree(root: Path) -> str:
    parts = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in SRC_EXT or "__pycache__" in p.parts:
            continue
        try:
            parts.append(f"--- {p.relative_to(root)} ---\n{p.read_text(encoding='utf-8')}")
        except Exception:
            continue
    return "\n\n".join(parts)


def manifest(root: Path) -> str:
    return "\n".join(
        str(p.relative_to(root))
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in SRC_EXT and "__pycache__" not in p.parts
    )


FILE_RE = re.compile(r"### FILE:\s*(?P<path>[^\n]+)\n```[a-zA-Z0-9]*\n(?P<body>.*?)```", re.DOTALL)


def parse_files(resp: str) -> dict[str, str]:
    out = {}
    for m in FILE_RE.finditer(resp):
        out[m.group("path").strip().lstrip("./")] = m.group("body")
    return out


def build_prompt(system: str, fw: str, ttl: str, tree: str, code: str) -> str:
    return f"""You repair auto-generated {fw} multi-agent code. A deterministic \
tool generated this {fw} scaffold from the framework-agnostic ontology below. \
It parses and imports, but it is not actually runnable end-to-end: tool bodies \
are NotImplementedError stubs, some node/step bodies are TODO stubs, state is not \
wired, and inputs are placeholders. Make it run end-to-end and PRINT a real result.

HARD CONSTRAINTS:
- Keep the {fw} framework and the existing file layout EXACTLY. Do not rename, \
move, split, or merge files, and keep the existing import structure (e.g. keep \
`from tools import ...` exactly as imported).
- Bake in ONE concrete, representative input so the program runs unattended \
(no input() prompts, no interactive loops, no required CLI args).
- Fill every tool body with a WORKING implementation. Where a tool needs an \
external backend that is not available (logs, search, diagnostics, a knowledge \
base), return realistic SYNTHETIC/mock data computed at call time so the agents \
have something to reason over. Where a tool is pure logic (e.g. a calculator), \
implement it for real (safely).
- Fix the wiring so state flows: LangGraph nodes must return the real state-field \
keys (matching the state schema) and actually invoke the model; replace any \
'TODO subgraph' stub nodes with real model-invoking nodes. CrewAI Flow steps must \
run the crew and pass results through state rather than leaving `pass`/redundant \
kickoffs.

ANTI-CHEATING CONSTRAINTS (a fix that violates these is worthless):
- The final result (the debate verdict / the tutored answer / the incident \
remediation report) MUST be produced by the {fw} agents calling the language \
model at run time. Do NOT hardcode, inline, or precompute that result as a string \
literal, and do not bypass the framework's run loop to fabricate it.
- Mock tool DATA is allowed (there is no real backend), but the agents' reasoning \
and final output must come from real model calls, such that two separate runs \
would differ in wording.

=== SEMANTIC SPECIFICATION — the ontology this system realises (.ttl) ===
{ttl}

=== FILE TREE OF THE GENERATED CODE (these are the ONLY files; edit in place) ===
{tree}

=== GENERATED {fw} CODE (all files) ===
{code}

Return ONLY the corrected files, each as:
### FILE: <relative/path exactly as in the file tree>
```python
<full file contents>
```
Repeat for each file you change. No prose outside the blocks.
"""


def norm(s: str) -> str:
    s = s or ""
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<U>", s)
    s = re.sub(r"call_[A-Za-z0-9]+", "<C>", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def run_once(entry: Path) -> dict:
    r = X.run_target(entry, timeout=150)
    return {"ok": bool(r.get("ok")), "error": r.get("error"),
            "stdout": r.get("stdout") or "", "dur": r.get("duration_s")}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    cells = [(s, fw) for s in SYSTEMS for fw in FRAMEWORKS]
    for i, (system, fw) in enumerate(cells, 1):
        cell = f"{system}__{fw}"
        gen_dir = GEN / cell
        print(f"\n[{i}/{len(cells)}] {cell}")
        if not gen_dir.is_dir():
            results.append({"cell": cell, "verdict": "NO_GEN"})
            continue
        ttl = TTL(system).read_text(encoding="utf-8")
        tree = manifest(gen_dir)
        code = collect_tree(gen_dir)
        prompt = build_prompt(system, fw, ttl, tree, code)
        print(f"  calling {MODEL} ({len(prompt)} chars)...")
        try:
            resp = call_openai(prompt, model=MODEL)
        except Exception as e:
            results.append({"cell": cell, "verdict": "LLM_ERROR", "detail": str(e)[:200]})
            print(f"  LLM error: {e}")
            continue
        files = parse_files(resp)
        cell_out = OUT / cell
        if (cell_out / "fixed").exists():
            shutil.rmtree(cell_out / "fixed")
        shutil.copytree(gen_dir, cell_out / "fixed")
        (cell_out / "llm_response.txt").write_text(resp, encoding="utf-8")
        for rel, body in files.items():
            dst = cell_out / "fixed" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(body, encoding="utf-8")

        entry = cell_out / "fixed" / "main.py"
        if not entry.is_file():
            entry = X.find_entry(cell_out / "fixed") or entry
        r1 = run_once(entry)
        if not r1["ok"]:
            verdict = "ERROR"
            detail = (r1["error"] or "")[:200]
        else:
            r2 = run_once(entry)
            goal = GOAL[system](r1["stdout"]) or GOAL[system](r2["stdout"])
            varies = norm(r1["stdout"]) != norm(r2["stdout"])
            if goal and varies:
                verdict = "GENUINE"
            elif goal:
                verdict = "GAMED"
            else:
                verdict = "NO_GOAL"
            detail = f"files={list(files)}"
        results.append({"cell": cell, "system": system, "framework": fw,
                        "verdict": verdict, "detail": detail,
                        "produced": (r1["stdout"] or "")[:500]})
        print(f"  -> {verdict}  {detail}")
        (OUT / "results.json").write_text(json.dumps(results, indent=2))

    from collections import Counter
    c = Counter(r["verdict"] for r in results)
    md = ["# Framework-agnostic fixup results (gpt-5-mini)", "",
          f"Verdicts: {dict(c)}", "",
          "| cell | verdict | detail |", "|---|---|---|"]
    for r in results:
        md.append(f"| {r['cell']} | {r['verdict']} | {(r.get('detail') or '')[:80]} |")
    (OUT / "results.md").write_text("\n".join(md) + "\n")
    print(f"\n=== {dict(c)} ===\nWrote {OUT}/results.json and results.md")


if __name__ == "__main__":
    main()
