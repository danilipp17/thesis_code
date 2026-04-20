"""
syntax_validity.py
==================
Structural sanity check on a generated source tree.

For each ``.py`` file under the target directory, verify:

1. ``ast.parse`` succeeds (syntax is well-formed)
2. Every ``import`` / ``from ... import ...`` resolves against the current
   Python path (best-effort; a missing framework package is reported, not
   fatal).

Unlike :mod:`evaluation.metrics.execution_trace`, this metric does **not**
execute any code — only static checks. That makes it safe to run on
generated code without API keys or side-effects, so it is the default
post-generation metric in the generation pipeline.
"""

from __future__ import annotations

import ast
import importlib.util
import logging
from pathlib import Path

log = logging.getLogger("oscin.eval.syntax")

NAME = "syntax_validity"


# --------------------------------------------------------------------
# Individual checks
# --------------------------------------------------------------------


def _check_syntax(path: Path) -> dict | None:
    """Return a dict describing a syntax error, or None if OK."""
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        return None
    except SyntaxError as e:
        return {
            "file": str(path),
            "line": e.lineno,
            "msg": e.msg,
        }
    except Exception as e:
        return {"file": str(path), "msg": f"{type(e).__name__}: {e}"}


def _iter_import_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # Skip relative imports — they're resolved against the local pkg.
            if node.level and node.level > 0:
                continue
            if node.module:
                names.append(node.module.split(".")[0])
    return names


def _check_imports(path: Path, local_modules: set[str]) -> list[str]:
    """Return the list of imports that could not be resolved."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []  # already reported by _check_syntax
    missing: list[str] = []
    for name in _iter_import_names(tree):
        if name in local_modules:
            continue
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            spec = None
        if spec is None:
            missing.append(name)
    return missing


# --------------------------------------------------------------------
# Top-level
# --------------------------------------------------------------------


def compute(source_root: Path) -> dict:
    """Check syntax and import resolution for every .py under ``source_root``."""
    source_root = Path(source_root)
    if not source_root.exists():
        return {"metric": NAME, "error": f"not found: {source_root}"}

    if source_root.is_file() and source_root.suffix == ".py":
        files = [source_root]
    elif source_root.is_dir():
        files = sorted(
            p for p in source_root.rglob("*.py")
            if "__pycache__" not in p.parts
        )
    else:
        return {"metric": NAME, "error": f"not a .py file/dir: {source_root}"}

    local_modules = {p.stem for p in files}

    syntax_errors: list[dict] = []
    unresolved: dict[str, list[str]] = {}

    for p in files:
        err = _check_syntax(p)
        if err is not None:
            syntax_errors.append(err)
            continue
        missing = _check_imports(p, local_modules)
        if missing:
            unresolved[str(p)] = missing

    n_files = len(files)
    n_syntax_ok = n_files - len(syntax_errors)
    syntax_rate = round(n_syntax_ok / n_files, 3) if n_files else 0.0

    # Import resolution rate: fraction of files with zero unresolved imports.
    n_imports_ok = n_files - len(syntax_errors) - len(unresolved)
    import_rate = round(n_imports_ok / n_files, 3) if n_files else 0.0

    return {
        "metric": NAME,
        "source": str(source_root),
        "files_checked": n_files,
        "syntax_ok": n_syntax_ok,
        "syntax_rate": syntax_rate,
        "syntax_errors": syntax_errors,
        "import_rate": import_rate,
        "unresolved_imports": unresolved,
    }


def row(result: dict) -> dict:
    return {
        "syntax_rate": result.get("syntax_rate"),
        "import_rate": result.get("import_rate"),
        "files_checked": result.get("files_checked"),
    }


def summarize_markdown(result: dict) -> str:
    if "error" in result:
        return f"## Syntax validity\n- error: `{result['error']}`\n"
    lines = [
        "## Syntax validity (generated source)",
        f"- files checked: {result.get('files_checked')}",
        f"- syntax ok rate: {result.get('syntax_rate')} "
        f"({result.get('syntax_ok')}/{result.get('files_checked')})",
        f"- import resolution rate: {result.get('import_rate')}",
    ]
    errs = result.get("syntax_errors") or []
    if errs:
        lines.append(f"- syntax errors ({len(errs)}):")
        for e in errs[:10]:
            lines.append(f"  - `{e['file']}`:{e.get('line')}: {e.get('msg')}")
    unresolved = result.get("unresolved_imports") or {}
    if unresolved:
        lines.append(f"- files with unresolved imports ({len(unresolved)}):")
        for f, missing in list(unresolved.items())[:10]:
            lines.append(f"  - `{f}`: {', '.join(missing)}")
    return "\n".join(lines) + "\n"
