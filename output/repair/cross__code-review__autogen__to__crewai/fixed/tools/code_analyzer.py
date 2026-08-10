"""
Auto-generated tool: code_analyzer
Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

# We'll implement the analysis here so the Crew tool is functional at runtime.
import ast as python_ast


class code_analyzerSchema(BaseModel):
    code: str = Field(description="")
    language: str = Field(description="")


class code_analyzer(BaseTool):
    name: str = "code_analyzer"
    description: str = """Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns."""
    args_schema: Type[BaseModel] = code_analyzerSchema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: tools.code_analyzer

        Performs a lightweight static analysis using Python's ast module.
        Returns a human-readable list of issues.
        """
        code = kwargs.get("code", "")
        language = kwargs.get("language", "python")
        if language.lower() != "python":
            return f"Unsupported language: {language}"

        issues = []
        if not code:
            return "No code provided."

        try:
            tree = python_ast.parse(code)
            issues.append("Syntax: OK")
            for node in python_ast.walk(tree):
                # Detect bare except clauses
                if isinstance(node, python_ast.ExceptHandler) and getattr(node, "type", None) is None:
                    lineno = getattr(node, "lineno", "unknown")
                    issues.append(
                        f"Line {lineno}: Bare 'except' clause — should catch specific exceptions."
                    )
                # Detect use of eval() calls (common security issue)
                if isinstance(node, python_ast.Call) and isinstance(node.func, python_ast.Name) and node.func.id == "eval":
                    lineno = getattr(node, "lineno", "unknown")
                    issues.append(f"Line {lineno}: Use of eval() detected — potential code injection vulnerability.")
                # Detect exec() usage
                if isinstance(node, python_ast.Call) and isinstance(node.func, python_ast.Name) and node.func.id == "exec":
                    lineno = getattr(node, "lineno", "unknown")
                    issues.append(f"Line {lineno}: Use of exec() detected — potential code injection vulnerability.")
                # Detect duplicate imports (simple heuristic)
                if isinstance(node, python_ast.Import):
                    # nothing here for now; placeholder for extensibility
                    pass
        except SyntaxError as e:
            issues.append(f"Syntax error at line {e.lineno}: {e.msg}")

        return "\n".join(issues)
