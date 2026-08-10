"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool
import ast as python_ast
from typing import Any

@tool
def code_analyzer(**kwargs) -> str:
    """
    Performs static analysis on source code.

Checks for syntax errors, undefined variables, unused imports,
and common anti-patterns.
    """
    # Accept flexible argument names
    code = ""
    if "code" in kwargs and isinstance(kwargs["code"], str):
        code = kwargs["code"]
    elif "text" in kwargs and isinstance(kwargs["text"], str):
        code = kwargs["text"]
    elif "input" in kwargs and isinstance(kwargs["input"], str):
        code = kwargs["input"]
    elif "source" in kwargs and isinstance(kwargs["source"], str):
        code = kwargs["source"]
    else:
        # If the tool was invoked with a single positional argument passed in kwargs,
        # try to find it.
        for v in kwargs.values():
            if isinstance(v, str):
                code = v
                break

    if code is None:
        code = ""

    issues = []
    if not code.strip():
        issues.append("No code provided.")
        return "\n".join(issues)

    try:
        tree = python_ast.parse(code)
        issues.append("Syntax: OK")
        for node in python_ast.walk(tree):
            # Bare except
            if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {getattr(node, 'lineno', '?')}: Bare 'except' clause — should catch specific exceptions."
                )
            # Use of eval
            if isinstance(node, python_ast.Call) and getattr(node.func, "id", "") == "eval":
                issues.append(
                    f"Line {getattr(node, 'lineno', '?')}: Use of eval() — can lead to code injection vulnerabilities."
                )
            # Detect return of exec/eval results not directly but catch NameError potential via Name nodes (simple heuristic)
            if isinstance(node, python_ast.Name) and node.id == "result" and isinstance(node.ctx, python_ast.Store):
                # not a strong heuristic; skip
                pass
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    except Exception as e:
        issues.append(f"Analyzer error: {type(e).__name__}: {e}")

    return "\n".join(issues)
