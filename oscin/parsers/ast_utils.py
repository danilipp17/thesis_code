"""
ast_utils.py
============
Shared AST parsing utilities for framework-specific source code parsers.
Provides common functions for traversing, inspecting, and extracting
data from Python AST nodes.
"""

import ast
from typing import Any, Optional


def inherits_from(class_node: ast.ClassDef, base_name: str) -> bool:
    """Check if a class inherits from a given base (by simple name)."""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == base_name:
            return True
        if isinstance(base, ast.Subscript):
            if isinstance(base.value, ast.Name) and base.value.id == base_name:
                return True
        if isinstance(base, ast.Attribute) and base.attr == base_name:
            return True
    return False


def has_decorator(node: ast.AST, decorator_name: str) -> bool:
    """Check if a class or function has a given decorator."""
    if not hasattr(node, "decorator_list"):
        return False
    for deco in node.decorator_list:  # type: ignore[attr-defined]
        if isinstance(deco, ast.Name) and deco.id == decorator_name:
            return True
        if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name):
            if deco.func.id == decorator_name:
                return True
    return False


def iter_methods(class_node: ast.ClassDef):
    """Yield all method definitions in a class."""
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield item


def find_call_in_method(method: ast.FunctionDef, func_name: str) -> Optional[ast.Call]:
    """Find the first call to func_name() inside a method body."""
    for node in ast.walk(method):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == func_name:
                return node
    return None


def find_keyword(call_node: ast.Call, keyword: str) -> Optional[ast.keyword]:
    """Find a keyword argument in a function call."""
    for kw in call_node.keywords:
        if kw.arg == keyword:
            return kw
    return None


def extract_constant_value(node: Optional[ast.expr]) -> Optional[str]:
    """Extract a string constant from an AST node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_keyword_string(call: ast.Call, name: str) -> Optional[str]:
    """Extract a string keyword argument value, handling joined strings."""
    for kw in call.keywords:
        if kw.arg != name:
            continue
        if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
        # Handle parenthesized multi-line strings: ("part1" "part2")
        if isinstance(kw.value, ast.JoinedStr):
            try:
                return ast.literal_eval(kw.value)
            except (ValueError, TypeError):
                return ast.unparse(kw.value)
    return None


def extract_keyword_bool(call: ast.Call, name: str) -> Optional[bool]:
    """Extract a boolean keyword argument value."""
    kw = find_keyword(call, name)
    if kw and isinstance(kw.value, ast.Constant):
        return bool(kw.value.value)
    return None


def extract_keyword_int(call: ast.Call, name: str) -> Optional[int]:
    """Extract an integer keyword argument value."""
    kw = find_keyword(call, name)
    if kw and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
        return kw.value.value
    return None


def extract_keyword_name(call: ast.Call, name: str) -> Optional[str]:
    """Extract a Name reference (variable/class name) from a keyword."""
    kw = find_keyword(call, name)
    if kw and isinstance(kw.value, ast.Name):
        return kw.value.id
    return None


def extract_keyword_name_list(call: ast.Call, name: str) -> list[str]:
    """Extract a list of Name references from a keyword argument."""
    kw = find_keyword(call, name)
    if kw and isinstance(kw.value, ast.List):
        return [elt.id for elt in kw.value.elts if isinstance(elt, ast.Name)]
    return []


def collect_local_assignments(method: ast.FunctionDef) -> dict[str, str]:
    """
    Collect local variable assignments of the form ``x = ClassName(...)``
    inside a method body. Returns {variable_name: class_name}.
    """
    assignments: dict[str, str] = {}
    for stmt in method.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call):
                if isinstance(stmt.value.func, ast.Name):
                    assignments[target.id] = stmt.value.func.id
    return assignments


def extract_return_values(method: ast.FunctionDef) -> list[str]:
    """Extract all string return values from a method body."""
    values = []
    for node in ast.walk(method):
        if isinstance(node, ast.Return) and node.value:
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                values.append(node.value.value)
            elif isinstance(node.value, ast.Name): # Also handle return END
                values.append(node.value.id)
    return values


def extract_pydantic_fields(class_node: ast.ClassDef) -> dict[str, dict[str, str]]:
    """
    Extract field names, type annotations and Field descriptions
    from a Pydantic model. Returns {field_name: {"type": ..., "description": ...}}.
    """
    fields = {}
    for item in class_node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            type_str = ast.unparse(item.annotation) if item.annotation else "Any"
            desc = ""
            # Check for Field(..., description="...") in the default value
            if isinstance(item.value, ast.Call):
                for kw in item.value.keywords:
                    if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                        desc = str(kw.value.value)
            fields[item.target.id] = {"type": type_str, "description": desc}
    return fields


def get_call_name(node: ast.Call) -> str:
    """Get the simple name of a function/class being called."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def get_attr_value_name(node: ast.Attribute) -> Optional[str]:
    """If attribute is accessed on a Name, return that Name."""
    if isinstance(node.value, ast.Name):
        return node.value.id
    return None


def safe_key(name: str) -> str:
    """Convert a name to a safe dict key."""
    return name.replace(" ", "_").replace("-", "_").replace(".", "_")


def ast_to_string(node: Optional[ast.expr]) -> Optional[str]:
    """Convert an AST node to a plain string if possible."""
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    return None
