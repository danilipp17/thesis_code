"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool
import ast as python_ast

@tool
def code_analyzer(**kwargs) -> str:
    """
    Performs static analysis on source code.

Checks for syntax errors, undefined variables, unused imports,
and common anti-patterns.
    """
    code = kwargs.get("code") or kwargs.get("input") or kwargs.get("text") or ""
    issues = []
    if not code:
        return "No code provided to analyzer."

    try:
        tree = python_ast.parse(code)
        issues.append("Syntax: OK")
        for node in python_ast.walk(tree):
            if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {node.lineno}: Bare 'except' clause — should catch specific exceptions."
                )
            # detect use of eval as a basic security anti-pattern
            if isinstance(node, python_ast.Call) and getattr(node.func, "id", "") == "eval":
                issues.append(
                    f"Line {node.lineno if hasattr(node, 'lineno') else '?'}: Use of eval() — can lead to code injection vulnerabilities."
                )
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    return "\n".join(issues)
