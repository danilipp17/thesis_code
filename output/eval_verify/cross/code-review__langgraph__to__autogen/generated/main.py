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


async def main():
    stream = team.run_stream(
        task="f\"You are a senior software engineer with 15 years of experience in code review. Review the following code for correctness, readability, and best practices. Identify bugs, code smells, naming issues, and suggest improvements.\\n\\nCode:\\n{state['code']}\\n\\nAnalyzer output:\\n{analysis}\""
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())