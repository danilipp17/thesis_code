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
        "A helpful assistant that can plan trips."
    ),
)

local_agent = AssistantAgent(
    name="local_agent",
    model_client=model_client,
    system_message=(
        "A local assistant that can suggest local activities or places to visit."
    ),
)

language_agent = AssistantAgent(
    name="language_agent",
    model_client=model_client,
    system_message=(
        "A helpful assistant that can provide language tips for a given destination."
    ),
)

travel_summary_agent = AssistantAgent(
    name="travel_summary_agent",
    model_client=model_client,
    system_message=(
        "An assistant that can summarize the travel plan."
    ),
)

# -- Team --
text_termination = TextMentionTermination("TERMINATE")
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination | text_termination

team = SelectorGroupChat(
    participants=[planner_agent, local_agent, language_agent, travel_summary_agent],
    model_client=model_client,
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Plan a 10 day trip to Luxembourg."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())