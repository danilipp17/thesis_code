"""
Auto-generated AutoGen application: tech_blog
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
researcher = AssistantAgent(
    name="researcher",
    model_client=model_client,
    system_message=(
        ""
    ),
)

writer = AssistantAgent(
    name="writer",
    model_client=model_client,
    system_message=(
        ""
    ),
)

editor = AssistantAgent(
    name="editor",
    model_client=model_client,
    system_message=(
        ""
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[researcher, writer, editor],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="f'Research the following topic and provide a comprehensive summary: {topic}'"
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())