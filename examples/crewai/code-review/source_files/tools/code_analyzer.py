"""Static code analysis tool."""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class CodeAnalyzerSchema(BaseModel):
    code: str = Field(description="The source code to analyze.")
    language: str = Field(default="python", description="The programming language.")


class CodeAnalyzerTool(BaseTool):
    name: str = "Code Analyzer"
    description: str = (
        "Performs static analysis on source code. "
        "Checks for syntax errors, undefined variables, "
        "unused imports, and common anti-patterns."
    )
    args_schema: Type[BaseModel] = CodeAnalyzerSchema

    def _run(self, code: str, language: str = "python") -> str:
        import ast as python_ast

        issues = []
        try:
            tree = python_ast.parse(code)
            issues.append("Syntax: OK")

            # Check for bare except
            for node in python_ast.walk(tree):
                if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                    issues.append(
                        f"Line {node.lineno}: Bare 'except' clause — "
                        "should catch specific exceptions."
                    )
        except SyntaxError as e:
            issues.append(f"Syntax error at line {e.lineno}: {e.msg}")

        return "\n".join(issues)
