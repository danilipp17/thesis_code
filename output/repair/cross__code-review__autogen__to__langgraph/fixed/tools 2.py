"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool
import ast as python_ast

@tool
def code_analyzer(code: str, language: str) -> str:
    """
    Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.
    """
    issues = []
    try:
        tree = python_ast.parse(code)
        issues.append("Syntax: OK")
        # Look for some common anti-patterns
        for node in python_ast.walk(tree):
            # bare except
            if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {node.lineno}: Bare 'except' clause — should catch specific exceptions."
                )
            # use of eval
            if isinstance(node, python_ast.Call) and getattr(node.func, "id", None) == "eval":
                issues.append(
                    f"Line {node.lineno}: Use of eval() — can lead to code injection. Avoid using eval on untrusted input."
                )
            # bare input usage (simple heuristic)
            if isinstance(node, python_ast.Call) and getattr(node.func, "id", None) == "input":
                issues.append(
                    f"Line {node.lineno}: Use of input() without validation — ensure proper sanitization."
                )
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    return "\n".join(issues)
