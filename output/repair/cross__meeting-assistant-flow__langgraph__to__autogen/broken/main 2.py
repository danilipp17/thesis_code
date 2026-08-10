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


model_client = OpenAIChatCompletionClient(model="gpt-4o")


# -- Agents --
analyze_meeting = AssistantAgent(
    name="analyze_meeting",
    model_client=model_client,
    system_message=(
        "Extract actionable tasks from a meeting transcript."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[analyze_meeting],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="f\"Analyze the provided meeting transcript and generate a JSON list of {{name, description}} objects.\\n\\nTranscript:\\n{state['transcript']}\""
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())