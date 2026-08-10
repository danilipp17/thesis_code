"""
Auto-generated AutoGen application: code_review
"""

import asyncio
import dotenv
from typing import Any, Dict, List, Optional

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

import ast as python_ast

model_client = OpenAIChatCompletionClient(model="gpt-4o")


# -- Agents --
code_reviewer = AssistantAgent(
    name="code_reviewer",
    model_client=model_client,
    system_message=(
        "Review the code for correctness, readability, and best practices."
    ),
)

security_auditor = AssistantAgent(
    name="security_auditor",
    model_client=model_client,
    system_message=(
        "Audit the code for security vulnerabilities with CWE classifications."
    ),
)

review_summarizer = AssistantAgent(
    name="review_summarizer",
    model_client=model_client,
    system_message=(
        "Synthesize review and audit findings into a structured report."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[code_reviewer, security_auditor, review_summarizer],
    termination_condition=termination,
)


CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""


def code_analyzer(code: str) -> str:
    """Performs static analysis on source code.

    Checks for syntax errors, bare excepts, and returns a short report.
    """
    issues = []
    try:
        tree = python_ast.parse(code)
        issues.append("Syntax: OK")
        for node in python_ast.walk(tree):
            if isinstance(node, python_ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {node.lineno}: Bare 'except' clause — should catch specific exceptions."
                )
            # detect use of eval as a simple heuristic
            if isinstance(node, python_ast.Call) and getattr(node.func, "id", "") == "eval":
                issues.append("Use of eval detected: potential security risk (injection).")
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    return "\n".join(issues)


async def main():
    # Prepare the concrete task text by interpolating actual code and analyzer output.
    analysis = code_analyzer(CODE_TO_REVIEW)
    task_text = (
        "You are a senior software engineer with 15 years of experience in code review. "
        "Review the following code for correctness, readability, and best practices. "
        "Identify bugs, code smells, naming issues, and suggest improvements.\n\n"
        f"Code:\n{CODE_TO_REVIEW}\n\nAnalyzer output:\n{analysis}"
    )

    # Run the team with the prepared task text so the LLMs receive the real code and analysis.
    stream = team.run_stream(task=task_text)
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
