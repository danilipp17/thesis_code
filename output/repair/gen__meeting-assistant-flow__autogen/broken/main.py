"""
Auto-generated AutoGen application: meeting_assistant_flow
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
from tools import save_tasks_to_trello, send_message_to_channel

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
save_tasks_to_trello_tool = FunctionTool(
    save_tasks_to_trello,
    description="Push each task to a Trello board (stub).",
)
send_message_to_channel_tool = FunctionTool(
    send_message_to_channel,
    description="Post a message to a Slack channel (stub).",
)

# -- Agents --
meeting_analyzer = AssistantAgent(
    name="meeting_analyzer",
    model_client=model_client,
    system_message=(
        "You are an expert in analyzing meeting transcripts and summarizing the discussions into actionable tasks. Analyze the provided meeting transcript and generate a set of detailed, well-organized issues based on the discussion. Return the result as a JSON list of {name: str, description: str} objects."
    ),
)

# -- Team --

team = RoundRobinGroupChat(
    participants=[meeting_analyzer],
    max_turns=1,
)


async def main():
    stream = team.run_stream(
        task="f'Analyze the following meeting transcript and extract actionable tasks.\\n\\nTranscript:\\n{transcript}'"
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())