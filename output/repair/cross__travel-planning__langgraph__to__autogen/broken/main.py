"""
Auto-generated AutoGen application: travel_planning
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
planner_agent = AssistantAgent(
    name="planner_agent",
    model_client=model_client,
    system_message=(
        "Sketch the initial itinerary."
    ),
)

local_agent = AssistantAgent(
    name="local_agent",
    model_client=model_client,
    system_message=(
        "Add local activities."
    ),
)

language_agent = AssistantAgent(
    name="language_agent",
    model_client=model_client,
    system_message=(
        "Add language/communication tips."
    ),
)

travel_summary_agent = AssistantAgent(
    name="travel_summary_agent",
    model_client=model_client,
    system_message=(
        "Integrate everything into the final plan."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[planner_agent, local_agent, language_agent, travel_summary_agent],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="f\"Suggest a travel plan for the request: {state['request']}\""
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())