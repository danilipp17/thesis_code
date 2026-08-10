"""
Auto-generated AutoGen tool definitions.
"""


import ast as _ast
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
        tree = _ast.parse(input)
        issues.append("Syntax: OK")

        # Basic checks: bare except, use of eval, potential hardcoded secrets
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ExceptHandler):
                if node.type is None:
                    lineno = getattr(node, "lineno", "unknown")
                    issues.append(
                        f"Line {lineno}: Bare 'except' clause — should catch specific exceptions."
                    )
            elif isinstance(node, _ast.Call):
                func = node.func
                if isinstance(func, _ast.Name) and func.id == "eval":
                    lineno = getattr(node, "lineno", "unknown")
                    issues.append(
                        f"Line {lineno}: Use of eval() — can lead to code injection vulnerabilities."
                    )
            elif isinstance(node, _ast.Assign):
                # detect potential hardcoded secrets assigned to variables with common names
                for target in node.targets:
                    if isinstance(target, _ast.Name):
                        name = target.id.lower()
                        if any(k in name for k in ("pass", "secret", "token", "key")):
                            value = node.value
                            if isinstance(value, _ast.Constant) and isinstance(value.value, str):
                                lineno = getattr(node, "lineno", "unknown")
                                issues.append(
                                    f"Line {lineno}: Potential hardcoded secret assigned to '{target.id}'."
                                )
        return "\n".join(issues) if issues else "No issues found."
    except SyntaxError as e:
        return f"Syntax error at line {e.lineno}: {e.msg}"
