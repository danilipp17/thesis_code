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
    description="Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.",
)

# -- Agents --
code_reviewer = AssistantAgent(
    name="Code_Reviewer",
    model_client=model_client,
    tools=[code_analyzer_tool],
    system_message=(
        "You are a senior software engineer with 15 years of experience in code review. Review the code for correctness, readability, and best practices. Identify bugs, code smells, naming issues, and suggest improvements. Use the code analyzer tool to check for syntax and structural issues."
    ),
)

security_auditor = AssistantAgent(
    name="Security_Auditor",
    model_client=model_client,
    tools=[code_analyzer_tool],
    system_message=(
        "You are a certified security professional specializing in application security. Audit the code for security vulnerabilities including injection attacks, hardcoded secrets, insecure data handling, missing input validation, and OWASP Top 10 issues. Provide CWE classifications for each finding."
    ),
)

review_summarizer = AssistantAgent(
    name="Review_Summarizer",
    model_client=model_client,
    system_message=(
        "You are a technical lead who synthesizes feedback from code reviewers and security auditors. Compile all findings into a structured review report. Provide a verdict: APPROVED if no critical or major issues, otherwise REQUEST CHANGES. Include a summary, critical count, and action items. When done, reply with TERMINATE."
    ),
)

# -- Team --

team = RoundRobinGroupChat(
    participants=[code_reviewer, security_auditor, review_summarizer],
    max_turns=3,
)


async def main():
    stream = team.run_stream(
        task="f'Review the following code for quality and security:\\n{code_to_review}'"
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())