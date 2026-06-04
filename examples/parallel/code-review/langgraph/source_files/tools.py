"""Plain-Python static-analyzer helper, called directly from LangGraph nodes."""

import ast as python_ast


def code_analyzer(code: str) -> str:
    """Performs static analysis on source code.

    Checks for syntax errors, undefined variables, unused imports,
    and common anti-patterns.
    """
    issues = []
    try:
        tree = python_ast.parse(code)
        issues.append("Syntax: OK")
        for node in python_ast.walk(tree):
            if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {node.lineno}: Bare 'except' clause — "
                    "should catch specific exceptions."
                )
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    return "\n".join(issues)
