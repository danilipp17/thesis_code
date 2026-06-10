"""
Corrected AST diff that fixes the four issues found in the audit:

  1. Drop ``decorator_args`` entirely. It is redundant with ``decorators``
     (every string-literal decorator arg is already in the decorator string)
     and it only fires on 3 of 18 cells in the corpus, contributing free 1.0
     to the other 15 via the empty-set rule.

  2. ``class_bases`` now stores only the base tuple, not the class name.
     The class name is already in the ``classes`` feature, so including it
     twice double-counts a class rename.

  3. Per-feature F1 returns ``None`` for empty/empty classes. The aggregator
     skips them so they neither inflate nor deflate the macro average.

  4. The overall F1 is the macro F1 — the arithmetic mean of per-feature F1
     — as the methodology section claims. Macro P and macro R are still
     reported for transparency.

Run this script to re-compute the corrected AST diff over all 18 generation
cells and the 36 cross-framework cells, and compare against the as-implemented
numbers.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Re-use feature extractor helpers from the original implementation
from evaluation.metrics.ast_diff import (  # noqa: E402
    _name, _decorator_key, _unparse, _extract_state_fields, _is_state_class,
    _extract_graph_calls, collect_python_files,
)

FEATURE_KEYS = (
    "imports", "classes", "class_bases", "functions",
    "decorators", "state_fields", "state_annotations", "graph_calls",
)  # NOTE: decorator_args removed (Finding 2)


def extract_features(path: Path) -> dict[str, set]:
    """Same as original but: (a) no decorator_args, (b) class_bases without class name."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {k: set() for k in FEATURE_KEYS}

    imports: set[str] = set()
    classes: set[str] = set()
    class_bases: set[str] = set()
    functions: set[str] = set()
    decorators: set[str] = set()
    state_fields: set[str] = set()
    state_annotations: set[tuple[str, str]] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
            base_names = sorted([_name(b) or "?" for b in node.bases])
            # Fix 3: store only the base tuple, not the class name
            class_bases.add(",".join(base_names))
            if _is_state_class(node):
                for fname, ann in _extract_state_fields(node):
                    state_fields.add(fname)
                    state_annotations.add((fname, ann))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
            for dec in node.decorator_list:
                decorators.add(_decorator_key(dec))

    return {
        "imports": imports,
        "classes": classes,
        "class_bases": class_bases,
        "functions": functions,
        "decorators": decorators,
        "state_fields": state_fields,
        "state_annotations": state_annotations,
        "graph_calls": _extract_graph_calls(tree),
    }


def merge_features(paths: list[Path]) -> dict[str, set]:
    merged: dict[str, set] = {k: set() for k in FEATURE_KEYS}
    for p in paths:
        for k, v in extract_features(p).items():
            merged[k].update(v)
    return merged


def _prf(ref: set, cand: set) -> tuple[float | None, float | None, float | None]:
    """Returns (P, R, F1) or (None, None, None) when ref=cand=∅."""
    if not ref and not cand:
        return None, None, None
    inter = ref & cand
    p = len(inter) / len(cand) if cand else 0.0
    r = len(inter) / len(ref) if ref else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def compute(ref_root: Path, cand_root: Path) -> dict:
    ref_paths = collect_python_files(ref_root)
    cand_paths = collect_python_files(cand_root)
    if not ref_paths or not cand_paths:
        return {"error": "no python files"}
    ref = merge_features(ref_paths)
    cand = merge_features(cand_paths)

    per_feature = {}
    nonempty_fs, nonempty_ps, nonempty_rs = [], [], []
    for k in FEATURE_KEYS:
        rs = ref.get(k, set()); cs = cand.get(k, set())
        p, r, f = _prf(rs, cs)
        per_feature[k] = {
            "ref_count": len(rs), "cand_count": len(cs),
            "precision": p, "recall": r, "f1": f,
            "applicable": p is not None,
        }
        if p is not None:
            nonempty_ps.append(p); nonempty_rs.append(r); nonempty_fs.append(f)
    # Fix 4: macro F1 = mean of per-feature F1
    macro_f1 = round(mean(nonempty_fs), 3) if nonempty_fs else 0.0
    macro_p = round(mean(nonempty_ps), 3) if nonempty_ps else 0.0
    macro_r = round(mean(nonempty_rs), 3) if nonempty_rs else 0.0
    return {
        "overall": {"macro_f1": macro_f1, "macro_p": macro_p, "macro_r": macro_r},
        "per_feature": per_feature,
        "applicable_features": len(nonempty_fs),
    }


# ----------------------------------------------------------------------
# Re-run over the corpus, compare against the as-implemented headline
# ----------------------------------------------------------------------

def main() -> None:
    from evaluation.metrics.ast_diff import compute as compute_orig

    FAMILIES = ["joke", "code-review", "tech-blog",
                "meeting-assistant-flow", "travel-planning", "react"]
    FRAMEWORKS = ["crewai", "langgraph", "autogen"]

    gen_rows = []
    for fam in FAMILIES:
        for fw in FRAMEWORKS:
            ref_dir = Path(f"/Users/danilippmann/Documents/Work/thesis_code/examples/parallel/{fam}/{fw}/source_files")
            gen_dir = Path(f"/Users/danilippmann/Documents/Work/thesis_code/output/eval_verify/generation/{fam}__{fw}/generated")
            orig = compute_orig(ref_dir, gen_dir)
            fixed = compute(ref_dir, gen_dir)
            gen_rows.append({
                "cell": f"{fam}/{fw}",
                "orig_f1": orig["overall"]["f1"],
                "fixed_f1": fixed["overall"]["macro_f1"],
                "applicable": fixed["applicable_features"],
            })

    print("=== GENERATION (18 cells) ===")
    print(f"  {'cell':36s} {'orig F1':>8s}  {'fixed F1':>8s}  {'#feats':>8s}")
    for r in gen_rows:
        print(f"  {r['cell']:34s} {r['orig_f1']:>8.3f}  {r['fixed_f1']:>8.3f}  {r['applicable']:>8d}")
    print(f"\n  Mean orig F1  : {mean(r['orig_f1'] for r in gen_rows):.4f}")
    print(f"  Mean fixed F1 : {mean(r['fixed_f1'] for r in gen_rows):.4f}")

    # Cross-framework
    cross_rows = []
    for fam in FAMILIES:
        for s in FRAMEWORKS:
            for t in FRAMEWORKS:
                if s == t: continue
                ref_dir = Path(f"/Users/danilippmann/Documents/Work/thesis_code/examples/parallel/{fam}/{t}/source_files")
                gen_dir = Path(f"/Users/danilippmann/Documents/Work/thesis_code/output/eval_verify/cross/{fam}__{s}__to__{t}/generated")
                if not gen_dir.is_dir():
                    continue
                orig = compute_orig(ref_dir, gen_dir)
                fixed = compute(ref_dir, gen_dir)
                cross_rows.append({
                    "cell": f"{fam}/{s}->{t}",
                    "orig_f1": orig["overall"]["f1"],
                    "fixed_f1": fixed["overall"]["macro_f1"],
                    "applicable": fixed["applicable_features"],
                })

    print("\n=== CROSS-FRAMEWORK (36 cells) — per-direction means ===")
    print(f"  {'direction':24s} {'orig F1':>8s}  {'fixed F1':>8s}")
    for s in FRAMEWORKS:
        for t in FRAMEWORKS:
            if s == t: continue
            sub = [r for r in cross_rows if r["cell"].endswith(f"{s}->{t}")]
            if not sub: continue
            print(f"  {s+' -> '+t:22s} {mean(r['orig_f1'] for r in sub):>8.3f}  {mean(r['fixed_f1'] for r in sub):>8.3f}")
    print(f"\n  Mean orig F1  : {mean(r['orig_f1'] for r in cross_rows):.4f}")
    print(f"  Mean fixed F1 : {mean(r['fixed_f1'] for r in cross_rows):.4f}")

    out = Path(ROOT / "output" / "ast_diff_audit")
    out.mkdir(parents=True, exist_ok=True)
    (out / "generation.json").write_text(json.dumps(gen_rows, indent=2))
    (out / "crossfw.json").write_text(json.dumps(cross_rows, indent=2))
    print(f"\nWrote {out}/generation.json and {out}/crossfw.json")


if __name__ == "__main__":
    main()
