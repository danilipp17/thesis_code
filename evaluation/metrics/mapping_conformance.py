"""
mapping_conformance.py
======================
Validates that a CrewAI Flow ↔ LangGraph translation respects the canonical
mapping rules defined in ``evaluation/mappings/crewai_flow_to_langgraph.yml``.

For each rule, count instances of the source-side pattern in one tree and
the target-side pattern in the other. Conformance per rule = min(src, tgt)
/ max(src, tgt) (1.0 if both zero — rule simply doesn't apply to this
example). Overall conformance = mean of per-rule scores.

The metric is direction-aware:
- ``direction="lg_to_cf"``  — original is LangGraph, target is CrewAI Flow.
- ``direction="cf_to_lg"``  — original is CrewAI Flow, target is LangGraph.

A rule with ``bidirectional: false`` only contributes in one direction
(see ``fan_in`` / ``fan_in_or`` — LangGraph has no first-class equivalent).
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("oscin.eval.mapping")

NAME = "mapping_conformance"

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "mappings" / "crewai_flow_to_langgraph.yml"


# --------------------------------------------------------------------
# YAML loading (no PyYAML dependency — minimal parser for this file)
# --------------------------------------------------------------------


def _load_rules(path: Path) -> list[dict]:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text()).get("rules", [])
    except ImportError:
        # Fall back to a tiny hand-rolled parser sufficient for our schema.
        return _parse_minimal_yaml(path.read_text())


def _parse_minimal_yaml(text: str) -> list[dict]:
    """Hand-rolled, just-good-enough YAML for our rule file.

    Supports:
      - top-level ``rules:`` list
      - ``- key: value`` entries with two-space indent nesting
      - inline ``{key: value, ...}`` and ``[a, b]`` (no nesting)
    """
    rules: list[dict] = []
    current: dict | None = None
    stack: list[tuple[int, dict]] = []
    in_rules_block = False

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if stripped == "rules:":
            in_rules_block = True
            continue
        if not in_rules_block:
            continue

        if stripped.startswith("- "):
            current = {}
            rules.append(current)
            stack = [(indent, current)]
            stripped = stripped[2:]

        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()

        # Pop frames whose indent is >= current
        while stack and indent < stack[-1][0]:
            stack.pop()
        if not stack:
            continue
        target = stack[-1][1]

        if not val:
            new = {}
            target[key] = new
            stack.append((indent + 2, new))
        else:
            target[key] = _parse_scalar_or_inline(val)

    return rules


def _parse_scalar_or_inline(v: str) -> Any:
    v = v.strip()
    if v.startswith("{") and v.endswith("}"):
        out = {}
        body = v[1:-1].strip()
        if not body:
            return out
        for part in _split_top_level(body, ","):
            k, _, val = part.partition(":")
            out[k.strip()] = _parse_scalar_or_inline(val.strip())
        return out
    if v.startswith("[") and v.endswith("]"):
        body = v[1:-1].strip()
        if not body:
            return []
        return [_parse_scalar_or_inline(p.strip()) for p in _split_top_level(body, ",")]
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    return v


def _split_top_level(s: str, sep: str) -> list[str]:
    parts = []
    depth = 0
    cur = []
    for c in s:
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
        if c == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    if cur:
        parts.append("".join(cur))
    return parts


# --------------------------------------------------------------------
# AST feature counting
# --------------------------------------------------------------------


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _walk_files(root: Path) -> list[ast.AST]:
    trees = []
    if root.is_file() and root.suffix == ".py":
        files = [root]
    elif root.is_dir():
        files = [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]
    else:
        files = []
    for p in files:
        try:
            trees.append(ast.parse(p.read_text(encoding="utf-8")))
        except SyntaxError as e:
            log.warning("syntax error in %s: %s", p, e)
    return trees


def count_pattern(trees: list[ast.AST], kind: str, match: dict) -> int:
    """Count occurrences of a (kind, match) pattern across all ASTs."""
    total = 0
    for tree in trees:
        total += _count_in_tree(tree, kind, match)
    return total


def _count_in_tree(tree: ast.AST, kind: str, match: dict) -> int:
    count = 0

    if kind == "class_base":
        target = match.get("base")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    n = _name(base) or ""
                    # Strip subscript: Flow[State] → Flow
                    if isinstance(base, ast.Subscript):
                        n = _name(base.value) or ""
                    if n == target or n.endswith("." + target):
                        count += 1
                        break

    elif kind in ("call_method", "call_with_const"):
        target_method = match.get("method")
        first_name = match.get("first_name")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            method = None
            if isinstance(fn, ast.Attribute):
                method = fn.attr
            elif isinstance(fn, ast.Name):
                method = fn.id
            if method != target_method:
                continue
            if first_name is not None:
                if not node.args:
                    continue
                if _name(node.args[0]) != first_name:
                    continue
            if kind == "call_with_const":
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    continue
            count += 1

    elif kind == "decorator":
        target = match.get("decorator")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    name = _decorator_name(dec)
                    if name == target:
                        count += 1
                        break

    elif kind == "any_decorator":
        targets = set(match.get("decorators") or [])
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if _decorator_name(dec) in targets:
                        count += 1
                        break

    elif kind == "decorator_arg":
        target_dec = match.get("decorator")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and _name(dec.func) == target_dec:
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            count += 1
                            break

    elif kind == "decorator_call_name":
        target_dec = match.get("decorator")
        inner_call = match.get("inner_call")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and _name(dec.func) == target_dec:
                        for a in dec.args:
                            if isinstance(a, ast.Call) and _name(a.func) == inner_call:
                                count += 1
                                break

    elif kind == "reducer_field":
        # Annotated[T, reducer]
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                ann = node.annotation
                if isinstance(ann, ast.Subscript) and (_name(ann.value) or "").endswith("Annotated"):
                    count += 1

    elif kind == "pydantic_default":
        # class with BaseModel base, field with default value
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = [_name(b) or "" for b in node.bases]
                if not any(b == "BaseModel" or b.endswith(".BaseModel") for b in base_names):
                    continue
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                        count += 1

    return count


def _decorator_name(dec: ast.AST) -> str:
    if isinstance(dec, ast.Call):
        return _name(dec.func) or ""
    return _name(dec) or ""


# --------------------------------------------------------------------
# Top-level metric
# --------------------------------------------------------------------


def compute(
    lg_root: Path,
    cf_root: Path,
    direction: str = "lg_to_cf",
    rules_path: Path | None = None,
) -> dict:
    """Score conformance of one tree against the other under canonical rules.

    ``direction`` selects which side is "source" and which is "target":
      - ``lg_to_cf``: LangGraph at lg_root translated to CrewAI at cf_root.
      - ``cf_to_lg``: CrewAI at cf_root translated to LangGraph at lg_root.
    """
    rules = _load_rules(rules_path or DEFAULT_RULES_PATH)
    lg_trees = _walk_files(lg_root)
    cf_trees = _walk_files(cf_root)

    per_rule = []
    scores = []
    for rule in rules:
        lg_kind = rule["lg"]["kind"]
        lg_match = rule["lg"].get("match", {})
        cf_kind = rule["cf"]["kind"]
        cf_match = rule["cf"].get("match", {})
        bidir = rule.get("bidirectional", True)

        if direction == "cf_to_lg" and not bidir:
            continue

        lg_count = count_pattern(lg_trees, lg_kind, lg_match)
        cf_count = count_pattern(cf_trees, cf_kind, cf_match)

        if direction == "lg_to_cf":
            src, tgt = lg_count, cf_count
        else:
            src, tgt = cf_count, lg_count

        if src == 0 and tgt == 0:
            score = None  # rule doesn't apply
        elif src == 0 or tgt == 0:
            score = 0.0
        else:
            score = round(min(src, tgt) / max(src, tgt), 3)

        if score is not None:
            scores.append(score)

        per_rule.append({
            "id": rule["id"],
            "description": rule["description"],
            "lg_count": lg_count,
            "cf_count": cf_count,
            "score": score,
            "bidirectional": bidir,
        })

    overall = round(sum(scores) / len(scores), 3) if scores else None

    return {
        "metric": NAME,
        "direction": direction,
        "lg_root": str(lg_root),
        "cf_root": str(cf_root),
        "applicable_rules": len(scores),
        "overall_score": overall,
        "per_rule": per_rule,
    }


def row(result: dict) -> dict:
    """Flat fields for the benchmark CSV."""
    return {
        "mapping_overall": result.get("overall_score"),
        "mapping_applicable_rules": result.get("applicable_rules"),
        "mapping_direction": result.get("direction"),
    }


def summarize_markdown(result: dict) -> str:
    if "error" in result:
        return f"## Mapping conformance\n- error: `{result['error']}`\n"
    lines = [
        "## Mapping conformance (CrewAI Flow ↔ LangGraph)",
        f"- direction: {result.get('direction')}",
        f"- overall: {result.get('overall_score')}",
        f"- applicable rules: {result.get('applicable_rules')}",
    ]
    for rule in result.get("per_rule") or []:
        lines.append(
            f"  - {rule['id']}: lg={rule['lg_count']} cf={rule['cf_count']} "
            f"score={rule['score']}"
        )
    return "\n".join(lines) + "\n"
