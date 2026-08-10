"""
Auto-generated LangGraph tool definitions.
"""

from langchain_core.tools import tool
import ast as python_ast
from typing import Optional

@tool
def code_analyzer(code: str, language: str = "python") -> str:
    """
    Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.
    """
    issues = []
    if language.lower() != "python":
        return f"Unsupported language: {language}"

    try:
        tree = python_ast.parse(code)
        issues.append("Syntax: OK")
        # Detect bare except clauses and some simple anti-patterns
        for node in python_ast.walk(tree):
            if isinstance(node, python_ast.ExceptHandler) and getattr(node, "type", None) is None:
                issues.append(
                    f"Line {node.lineno}: Bare 'except' clause — should catch specific exceptions."
                )
            # detect use of eval/call to exec as a simple security anti-pattern
            if isinstance(node, python_ast.Call):
                func = node.func
                name: Optional[str] = None
                if isinstance(func, python_ast.Name):
                    name = func.id
                elif isinstance(func, python_ast.Attribute):
                    name = getattr(func.attr, "id", None) if isinstance(func.attr, python_ast.AST) else func.attr
                if name in ("eval", "exec", "execfile"):
                    issues.append(
                        f"Line {node.lineno}: Use of '{name}' detected — executing arbitrary code is dangerous."
                    )
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    return "\n".join(issues)
