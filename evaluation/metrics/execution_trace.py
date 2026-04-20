"""
execution_trace.py
==================
Live execution comparison: runs the original and the generated entry-point
in subprocesses and compares outcomes.

The subprocess wraps the target with a tiny preamble that calls
``dotenv.load_dotenv()`` (so ``OPENAI_API_KEY`` from ``.env`` is available)
and then ``runpy.run_path``-s the target file. We capture:

- exit status / exception type
- duration
- stdout / stderr (last ~4 KB)

Comparison metric:

- ``ref_ok`` / ``cand_ok``       — did each side complete successfully?
- ``ok_match``                   — both succeeded
- ``error_match``                — same error type when both failed
- ``stdout_overlap``             — token-level Jaccard on stdout
- ``duration_ratio``             — min/max of the two durations

If the source file cannot run standalone (relative imports, missing
project package, missing third-party deps), the metric reports the
exception honestly rather than guessing. That is itself a signal:
"extracted source is not a runnable artifact in isolation."
"""

from __future__ import annotations

import logging
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

log = logging.getLogger("oscin.eval.exec")

NAME = "execution_trace"

PROJECT_ROOT = Path(__file__).resolve().parents[2]


_PREAMBLE = textwrap.dedent(
    """
    import sys, runpy, time, traceback, json
    from pathlib import Path

    target = Path(sys.argv[1]).resolve()
    out_marker = "__OSCIN_TRACE__"

    # Load .env from the project root or any parent of the target.
    try:
        from dotenv import load_dotenv
        for p in [target, *target.parents]:
            env = p / ".env"
            if env.is_file():
                load_dotenv(env)
                break
    except ImportError:
        pass

    # Make the target's directory importable (for sibling imports).
    sys.path.insert(0, str(target.parent))

    result = {"ok": False, "error": None, "duration_s": 0.0}
    t0 = time.perf_counter()
    try:
        runpy.run_path(str(target), run_name="__main__")
        result["ok"] = True
    except SystemExit as e:
        result["ok"] = e.code in (0, None)
        if not result["ok"]:
            result["error"] = f"SystemExit({e.code})"
    except BaseException as e:
        result["error"] = f"{type(e).__name__}: {e}"
    finally:
        result["duration_s"] = round(time.perf_counter() - t0, 3)
        print(out_marker + json.dumps(result))
    """
).strip()


def run_target(target: Path, timeout: float = 120.0) -> dict:
    """Run a single target file in a subprocess; return the parsed result dict."""
    target = target.resolve()
    if not target.is_file():
        return {"ok": False, "error": f"target not found: {target}", "stdout": "", "stderr": ""}
    cmd = [sys.executable, "-c", _PREAMBLE, str(target)]
    log.debug("running: %s", shlex.join(cmd))
    try:
        proc = subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s", "stdout": "", "stderr": ""}

    # Find the marker line and parse the JSON payload from it.
    marker = "__OSCIN_TRACE__"
    payload = None
    user_stdout_lines = []
    for line in proc.stdout.splitlines():
        idx = line.find(marker)
        if idx >= 0:
            import json as _json
            try:
                payload = _json.loads(line[idx + len(marker):])
            except _json.JSONDecodeError:
                pass
        else:
            user_stdout_lines.append(line)

    user_stdout = "\n".join(user_stdout_lines)
    if payload is None:
        # Subprocess crashed before the marker — capture what we can.
        return {
            "ok": False,
            "error": f"subprocess exit {proc.returncode}; no trace marker",
            "stdout": user_stdout[-4096:],
            "stderr": proc.stderr[-4096:],
            "duration_s": None,
        }
    payload["stdout"] = user_stdout[-4096:]
    payload["stderr"] = proc.stderr[-4096:]
    payload["subprocess_rc"] = proc.returncode
    return payload


def find_entry(path: Path) -> Path | None:
    """Find the entry-point .py file in a directory tree."""
    if path.is_file() and path.suffix == ".py":
        return path
    if not path.is_dir():
        return None
    for candidate in [path / "main.py", *sorted(path.glob("*.py"))]:
        if candidate.is_file():
            return candidate
    for c in path.rglob("main.py"):
        return c
    pys = list(path.rglob("*.py"))
    return pys[0] if pys else None


def _tokens(text: str) -> set[str]:
    return {tok.strip(".,:;()[]{}\"'") for tok in (text or "").split() if tok.strip()}


def compare(ref: dict, cand: dict) -> dict:
    """Compare two run_target results."""
    ref_ok = bool(ref.get("ok"))
    cand_ok = bool(cand.get("ok"))

    ref_tokens = _tokens(ref.get("stdout", ""))
    cand_tokens = _tokens(cand.get("stdout", ""))
    if ref_tokens or cand_tokens:
        stdout_overlap = round(
            len(ref_tokens & cand_tokens) / len(ref_tokens | cand_tokens), 3
        )
    else:
        stdout_overlap = 1.0 if ref_ok and cand_ok else 0.0

    durations = [ref.get("duration_s"), cand.get("duration_s")]
    if all(d is not None and d > 0 for d in durations):
        duration_ratio = round(min(durations) / max(durations), 3)
    else:
        duration_ratio = None

    error_match = (
        ref.get("error") and cand.get("error")
        and ref["error"].split(":")[0] == cand["error"].split(":")[0]
    )

    return {
        "metric": NAME,
        "ref_ok": ref_ok,
        "cand_ok": cand_ok,
        "ok_match": ref_ok and cand_ok,
        "ref_error": ref.get("error"),
        "cand_error": cand.get("error"),
        "error_match": bool(error_match),
        "ref_duration_s": ref.get("duration_s"),
        "cand_duration_s": cand.get("duration_s"),
        "duration_ratio": duration_ratio,
        "stdout_overlap": stdout_overlap,
        "ref_stdout_tail": (ref.get("stdout") or "")[-500:],
        "cand_stdout_tail": (cand.get("stdout") or "")[-500:],
    }


def compute(ref_root: Path, cand_root: Path, timeout: float = 120.0) -> dict:
    """Top-level entry: find an entry file in each root and compare runs."""
    ref_entry = find_entry(ref_root)
    cand_entry = find_entry(cand_root)
    if ref_entry is None or cand_entry is None:
        return {
            "metric": NAME,
            "error": f"entry file not found (ref={ref_entry}, cand={cand_entry})",
        }
    ref = run_target(ref_entry, timeout=timeout)
    cand = run_target(cand_entry, timeout=timeout)
    result = compare(ref, cand)
    result["ref_entry"] = str(ref_entry)
    result["cand_entry"] = str(cand_entry)
    return result


def row(result: dict) -> dict:
    """Flat fields for the benchmark CSV."""
    return {
        "exec_ok_match": result.get("ok_match"),
        "exec_ref_ok": result.get("ref_ok"),
        "exec_cand_ok": result.get("cand_ok"),
        "exec_stdout_overlap": result.get("stdout_overlap"),
        "exec_duration_ratio": result.get("duration_ratio"),
        "exec_ref_error": result.get("ref_error"),
        "exec_cand_error": result.get("cand_error"),
    }


def summarize_markdown(result: dict) -> str:
    if "error" in result:
        return f"## Execution trace\n- error: `{result['error']}`\n"
    if result.get("skipped"):
        return "## Execution trace\n- skipped\n"
    lines = [
        "## Execution trace",
        f"- ref_ok={result.get('ref_ok')} cand_ok={result.get('cand_ok')}",
        f"- ok_match={result.get('ok_match')} error_match={result.get('error_match')}",
        f"- stdout_overlap={result.get('stdout_overlap')}",
        f"- duration_ratio={result.get('duration_ratio')}",
    ]
    if result.get("ref_error"):
        lines.append(f"- ref_error: `{result['ref_error']}`")
    if result.get("cand_error"):
        lines.append(f"- cand_error: `{result['cand_error']}`")
    return "\n".join(lines) + "\n"
