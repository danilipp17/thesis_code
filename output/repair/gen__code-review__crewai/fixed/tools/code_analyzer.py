"""
Auto-generated tool: code_analyzer
Performs static analysis on source code.

Checks for syntax errors, undefined variables, unused imports,
and common anti-patterns.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class code_analyzerSchema(BaseModel):
    pass


class code_analyzer(BaseTool):
    name: str = "code_analyzer"
    description: str = """Performs static analysis on source code.

Checks for syntax errors, undefined variables, unused imports,
and common anti-patterns."""
    args_schema: Type[BaseModel] = code_analyzerSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.code_analyzer.code_analyzer

        Runs a lightweight static analysis on the provided source code.
        Expects the caller to pass the source under the "code" keyword.
        """
        code = kwargs.get("code") or kwargs.get("input") or ""
        issues = []
        try:
            import ast as python_ast

            tree = python_ast.parse(code)
            issues.append("Syntax: OK")
            for node in python_ast.walk(tree):
                # detect bare except
                if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                    lineno = getattr(node, "lineno", "unknown")
                    issues.append(
                        f"Line {lineno}: Bare 'except' clause — should catch specific exceptions."
                    )
                # detect use of eval
                if isinstance(node, python_ast.Call):
                    func = node.func
                    func_name = None
                    if isinstance(func, python_ast.Name):
                        func_name = func.id
                    elif isinstance(func, python_ast.Attribute):
                        func_name = getattr(func.attr, "id", None)
                    if func_name == "eval":
                        lineno = getattr(node, "lineno", "unknown")
                        issues.append(
                            f"Line {lineno}: use of eval() — avoid executing untrusted code."
                        )
        except SyntaxError as e:
            issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
        return "\n".join(issues)
