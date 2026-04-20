"""
ast_diff.py
===========
Structural AST diff between original source and generated source.

Extracts a normalized feature set from each side and compares them to
produce structural recall (fraction of original constructs that survived
the round-trip) and structural precision (fraction of generated
constructs that can be mapped back to something in the original).

Features extracted per Python file:

- ``imports``           — set of imported module names (``import X``, ``from X import ...``)
- ``classes``           — set of class names
- ``class_bases``       — set of ``"Class(Base1, Base2)"`` signatures
- ``functions``         — set of top-level/method function names
- ``decorators``        — set of ``"@name"`` or ``"@name(args...)"`` strings on funcs/methods
- ``decorator_args``    — set of (decorator_name, first_literal_arg) pairs (for CrewAI ``@start("x")``, ``@listen("x")``)
- ``state_fields``      — set of field names on TypedDict / BaseModel subclasses
- ``state_annotations`` — set of ``(field_name, annotation_source)`` pairs preserving ``Annotated[...]`` reducers
- ``graph_calls``       — set of ``(graph_var, method, first_arg_literal)`` for LangGraph StateGraph calls
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("oscin.eval.ast_diff")

NAME = "ast_diff"

# --------------------------------------------------------------------
# Feature extraction
# --------------------------------------------------------------------


def _literal(node: ast.AST) -> str | None:
    """Return a simple string literal if node is one, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _decorator_key(dec: ast.AST) -> str:
    """Canonical ``@name`` or ``@name(arg)`` string."""
    if isinstance(dec, ast.Call):
        n = _name(dec.func) or "?"
        args = []
        for a in dec.args:
            lit = _literal(a)
            if lit is not None:
                args.append(f'"{lit}"')
            else:
                args.append(_name(a) or "?")
        return f"@{n}({', '.join(args)})"
    n = _name(dec) or "?"
    return f"@{n}"


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "?"


def _extract_state_fields(cls: ast.ClassDef) -> list[tuple[str, str]]:
    """Return [(field_name, annotation_source)] for TypedDict / BaseModel fields."""
    out: list[tuple[str, str]] = []
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            out.append((stmt.target.id, _unparse(stmt.annotation)))
    return out


def _is_state_class(cls: ast.ClassDef) -> bool:
    for base in cls.bases:
        n = _name(base) or ""
        if n in ("TypedDict", "BaseModel"):
            return True
        if n.endswith(".TypedDict") or n.endswith(".BaseModel"):
            return True
    return False


def _extract_graph_calls(tree: ast.AST) -> set[tuple[str, str, str]]:
    """Find ``X.add_node(...)``, ``X.add_edge(...)``, ``X.add_conditional_edges(...)`` calls."""
    out: set[tuple[str, str, str]] = set()
    methods = {"add_node", "add_edge", "add_conditional_edges", "set_entry_point", "set_finish_point"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in methods:
            continue
        graph_var = _name(func.value) or "?"
        first_arg = ""
        if node.args:
            lit = _literal(node.args[0])
            if lit is not None:
                first_arg = lit
            else:
                first_arg = _name(node.args[0]) or _unparse(node.args[0])[:40]
        out.add((graph_var, func.attr, first_arg))
    return out


def extract_features(path: Path) -> dict[str, set]:
    """Extract structural features from a Python source file."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        log.warning("Syntax error parsing %s: %s", path, e)
        return {
            k: set() for k in (
                "imports", "classes", "class_bases", "functions",
                "decorators", "decorator_args", "state_fields",
                "state_annotations", "graph_calls",
            )
        }

    imports: set[str] = set()
    classes: set[str] = set()
    class_bases: set[str] = set()
    functions: set[str] = set()
    decorators: set[str] = set()
    decorator_args: set[tuple[str, str]] = set()
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
            base_names = [_name(b) or "?" for b in node.bases]
            class_bases.add(f"{node.name}({','.join(base_names)})")
            if _is_state_class(node):
                for fname, ann in _extract_state_fields(node):
                    state_fields.add(fname)
                    state_annotations.add((fname, ann))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
            for dec in node.decorator_list:
                decorators.add(_decorator_key(dec))
                if isinstance(dec, ast.Call) and dec.args:
                    lit = _literal(dec.args[0])
                    if lit is not None:
                        dec_name = _name(dec.func) or "?"
                        decorator_args.add((dec_name, lit))

    return {
        "imports": imports,
        "classes": classes,
        "class_bases": class_bases,
        "functions": functions,
        "decorators": decorators,
        "decorator_args": decorator_args,
        "state_fields": state_fields,
        "state_annotations": state_annotations,
        "graph_calls": _extract_graph_calls(tree),
    }


# --------------------------------------------------------------------
# File discovery
# --------------------------------------------------------------------


def find_main_file(root: Path) -> Path | None:
    """Find the most likely entry-point .py file in a directory tree."""
    if root.is_file() and root.suffix == ".py":
        return root
    if not root.is_dir():
        return None
    # Prefer main.py at top level
    candidates = [root / "main.py"]
    candidates += sorted(root.glob("*.py"))
    candidates += sorted(root.rglob("main.py"))
    for c in candidates:
        if c.is_file():
            return c
    # Fallback to the biggest .py
    pys = sorted(root.rglob("*.py"), key=lambda p: p.stat().st_size, reverse=True)
    return pys[0] if pys else None


def collect_python_files(root: Path) -> list[Path]:
    """Collect all .py files under root (or the file itself)."""
    if root.is_file() and root.suffix == ".py":
        return [root]
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts)


def merge_features(paths: list[Path]) -> dict[str, set]:
    """Extract features from each file and union them."""
    merged: dict[str, set] = {}
    for p in paths:
        for k, v in extract_features(p).items():
            merged.setdefault(k, set()).update(v)
    return merged


# --------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------


def _prf(ref: set, cand: set) -> tuple[float, float, float]:
    if not ref and not cand:
        return 1.0, 1.0, 1.0
    inter = ref & cand
    p = len(inter) / len(cand) if cand else 0.0
    r = len(inter) / len(ref) if ref else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return round(p, 3), round(r, 3), round(f, 3)


def _serializable(v: Any) -> Any:
    if isinstance(v, set):
        return sorted(str(x) for x in v)
    if isinstance(v, tuple):
        return list(v)
    return v


def compare(ref_paths: list[Path], cand_paths: list[Path]) -> dict:
    """Compare feature sets between reference and candidate source trees."""
    ref = merge_features(ref_paths)
    cand = merge_features(cand_paths)

    per_feature = {}
    prs = []
    rrs = []
    for key in ref.keys() | cand.keys():
        r_set = ref.get(key, set())
        c_set = cand.get(key, set())
        p, r, f = _prf(r_set, c_set)
        per_feature[key] = {
            "precision": p,
            "recall": r,
            "f1": f,
            "ref_count": len(r_set),
            "cand_count": len(c_set),
            "missing": sorted(
                _serializable(x) for x in r_set - c_set
            ),
            "extra": sorted(
                _serializable(x) for x in c_set - r_set
            ),
            "matched": sorted(
                _serializable(x) for x in r_set & c_set
            ),
        }
        prs.append(p)
        rrs.append(r)

    overall_p = round(sum(prs) / len(prs), 3) if prs else 0.0
    overall_r = round(sum(rrs) / len(rrs), 3) if rrs else 0.0
    overall_f = (
        round(2 * overall_p * overall_r / (overall_p + overall_r), 3)
        if (overall_p + overall_r) else 0.0
    )

    return {
        "metric": NAME,
        "overall": {
            "precision": overall_p,
            "recall": overall_r,
            "f1": overall_f,
        },
        "per_feature": per_feature,
        "ref_files": [str(p) for p in ref_paths],
        "cand_files": [str(p) for p in cand_paths],
    }


def compute(ref_root: Path, cand_root: Path) -> dict:
    """Top-level entry: compare all .py files under each root."""
    ref_paths = collect_python_files(ref_root)
    cand_paths = collect_python_files(cand_root)
    if not ref_paths or not cand_paths:
        return {
            "metric": NAME,
            "error": (
                f"No .py files found. ref={ref_root} ({len(ref_paths)} files), "
                f"cand={cand_root} ({len(cand_paths)} files)"
            ),
        }
    return compare(ref_paths, cand_paths)


def row(result: dict) -> dict:
    """Flat fields for the benchmark CSV."""
    overall = (result.get("overall") or {})
    per = (result.get("per_feature") or {})
    return {
        "ast_overall_f1": overall.get("f1"),
        "ast_overall_precision": overall.get("precision"),
        "ast_overall_recall": overall.get("recall"),
        "ast_decorator_args_f1": (per.get("decorator_args") or {}).get("f1"),
        "ast_state_fields_f1": (per.get("state_fields") or {}).get("f1"),
        "ast_imports_f1": (per.get("imports") or {}).get("f1"),
        "ast_functions_f1": (per.get("functions") or {}).get("f1"),
    }


def summarize_markdown(result: dict) -> str:
    if "error" in result:
        return f"## AST diff\n- error: `{result['error']}`\n"
    overall = result.get("overall") or {}
    lines = [
        "## AST diff (source vs generated)",
        f"- overall: P={overall.get('precision')} R={overall.get('recall')} F1={overall.get('f1')}",
    ]
    for feat, pr in (result.get("per_feature") or {}).items():
        lines.append(
            f"  - {feat}: ref={pr['ref_count']} cand={pr['cand_count']} F1={pr['f1']}"
        )
    return "\n".join(lines) + "\n"
