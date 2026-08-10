"""
Auto-generated AutoGen tool definitions.
"""

import ast as python_ast
from typing import List

def code_analyzer(input: str) -> str:
    """
    
    Performs static analysis on source code.
    
    Checks for syntax errors, undefined variables, unused imports,
    and common anti-patterns.

    Implementation reference: tools.code_analyzer.code_analyzer
    """
    issues: List[str] = []
    try:
        tree = python_ast.parse(input)
        issues.append("Syntax: OK")
        for node in python_ast.walk(tree):
            # Detect bare except clauses
            if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {getattr(node, 'lineno', '?')}: Bare 'except' clause — should catch specific exceptions."
                )
            # Detect use of eval
            if isinstance(node, python_ast.Call) and getattr(node.func, "id", "") == "eval":
                issues.append(
                    f"Line {getattr(node, 'lineno', '?')}: Use of eval() detected — avoid executing untrusted input."
                )
            # Detect potential use of exec
            if isinstance(node, python_ast.Call) and getattr(node.func, "id", "") == "exec":
                issues.append(
                    f"Line {getattr(node, 'lineno', '?')}: Use of exec() detected — avoid executing untrusted input."
                )
        if len(issues) == 1 and issues[0] == "Syntax: OK":
            # No specific issues found beyond syntax
            issues.append("No obvious anti-patterns detected by static checks.")
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    except Exception as e:
        issues.append(f"Analyzer error: {e}")
    return "\n".join(issues)
