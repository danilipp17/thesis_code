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

from autogen_core.tools import FunctionTool
from tools import code_analyzer

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
code_analyzer_tool = FunctionTool(
    code_analyzer,
    description="Performs static analysis on source code.  Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.",
)

# -- Agents --
code_reviewer = AssistantAgent(
    name="Code_Reviewer",
    model_client=model_client,
    tools=[code_analyzer_tool],
    system_message=(
        "Review code for correctness, readability, and best practices. A senior software engineer with 15 years of experience in code review who identifies bugs, code smells, naming issues, and suggests improvements, using the code analyzer tool to check for syntax and structural issues."
    ),
)

security_auditor = AssistantAgent(
    name="Security_Auditor",
    model_client=model_client,
    tools=[code_analyzer_tool],
    system_message=(
        "Audit code for security vulnerabilities including injection attacks, hardcoded secrets, insecure data handling, missing input validation, and OWASP Top 10 issues. A certified security professional specializing in application security who provides CWE classifications for each finding."
    ),
)

review_summarizer = AssistantAgent(
    name="Review_Summarizer",
    model_client=model_client,
    system_message=(
        "Compile findings from reviewer and auditor into a structured review report with a clear verdict and action items. A technical lead who synthesizes feedback from code reviewers and security auditors and gives a verdict of APPROVED if no critical or major issues exist, otherwise REQUEST CHANGES."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[code_reviewer, security_auditor, review_summarizer],
    termination_condition=termination,
)

# Representative code to review (matches original example)
CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""

async def main():
    # Interpolate the actual code into the task prompt (was previously a literal placeholder)
    task_prompt = (
        "Review the following code for correctness, readability, and best practices. Use the code analyzer tool.\n\n"
        + CODE_TO_REVIEW
    )

    stream = team.run_stream(
        task=task_prompt
    )
    # Console will consume and print the stream to stdout
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
