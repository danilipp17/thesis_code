"""
Auto-generated AutoGen tool definitions.
"""

import ast as python_ast
from typing import Any


def code_analyzer(code: str, language: str) -> str:
    """
    
    Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.

    Implementation reference: tools.code_analyzer
    """
    # Provide a simple static analysis for Python code. Keep the implementation lightweight
    # but useful for the agents. Do not hardcode any outputs — analysis depends on the input.
    issues = []
    # Accept None or empty language by defaulting to python
    if not language:
        language = "python"

    if language.lower() != "python":
        return f"Unsupported language: {language}. This analyzer only supports Python."

    try:
        tree = python_ast.parse(code)
        issues.append("Syntax: OK")

        # Track assigned names to help detect unused imports/variables (simple heuristics)
        assigned_names = set()
        imported_names = set()
        used_names = set()

        for node in python_ast.walk(tree):
            # Detect bare except clauses
            if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {node.lineno}: Bare 'except' clause — should catch specific exceptions."
                )

            # Detect eval usage (security anti-pattern)
            if isinstance(node, python_ast.Call):
                func = node.func
                if isinstance(func, python_ast.Name) and func.id == "eval":
                    issues.append(
                        f"Line {node.lineno}: Use of eval() — may lead to code injection. "
                        "Consider safer parsing or restricted evaluation."
                    )
                # exec usage
                if isinstance(func, python_ast.Name) and func.id == "exec":
                    issues.append(
                        f"Line {node.lineno}: Use of exec() — can execute arbitrary code and is unsafe."
                    )

            # Track imports
            if isinstance(node, python_ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name.split(".")[0])
            if isinstance(node, python_ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)

            # Track assigned and used names
            if isinstance(node, python_ast.Assign):
                for target in node.targets:
                    if isinstance(target, python_ast.Name):
                        assigned_names.add(target.id)
            if isinstance(node, python_ast.Name):
                used_names.add(node.id)

            # Detect calls to potentially dangerous functions (simple list)
            if isinstance(node, python_ast.Call) and isinstance(node.func, python_ast.Attribute):
                # e.g., subprocess.Popen, os.system
                attr = node.func
                if (
                    isinstance(attr.value, python_ast.Name)
                    and attr.value.id in {"os", "subprocess"}
                    and isinstance(attr.attr, str)
                ):
                    issues.append(
                        f"Line {node.lineno}: Potentially dangerous call '{attr.value.id}.{attr.attr}' — "
                        "ensure inputs are validated and consider safer alternatives."
                    )

        # Unused imports heuristic
        unused_imports = sorted(list(imported_names - used_names))
        for name in unused_imports:
            issues.append(f"Unused import detected: {name}")

        # Unused assignments heuristic
        unused_assignments = sorted(list(assigned_names - used_names))
        for name in unused_assignments:
            issues.append(f"Assigned but unused variable: {name}")

        if len(issues) == 1 and issues[0] == "Syntax: OK":
            issues.append("No obvious structural issues found.")

    except SyntaxError as e:
        issues = [f"Syntax error at line {e.lineno}: {e.msg}"]

    return "\n".join(issues)
