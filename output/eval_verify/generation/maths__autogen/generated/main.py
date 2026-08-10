"""
Auto-generated AutoGen application: maths
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
from tools import add, subtract, multiply

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
add_tool = FunctionTool(
    add,
    description="Add two integers.",
)
subtract_tool = FunctionTool(
    subtract,
    description="Subtract two integers.",
)
multiply_tool = FunctionTool(
    multiply,
    description="Multiply two integers.",
)

# -- Agents --
our_agent = AssistantAgent(
    name="our_agent",
    model_client=model_client,
    tools=[add_tool, subtract_tool, multiply_tool],
    system_message=(
        "You are my AI assistant, please answer my query to the best of your ability."
    ),
)

# -- Team --

team = RoundRobinGroupChat(
    participants=[our_agent],
    max_turns=1,
)


async def main():
    stream = team.run_stream(
        task="Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())