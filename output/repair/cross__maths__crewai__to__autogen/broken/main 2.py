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
    description="This is an addition function that adds 2 numbers together.",
)
subtract_tool = FunctionTool(
    subtract,
    description="Subtraction function.",
)
multiply_tool = FunctionTool(
    multiply,
    description="Multiplication function.",
)

# -- Agents --
our_agent = AssistantAgent(
    name="Maths_Reasoning_Assistant",
    model_client=model_client,
    tools=[add_tool, subtract_tool, multiply_tool],
    system_message=(
        "Answer the user query, calling arithmetic tools when needed. You are an AI assistant that answers user queries to the best of your ability, using the available tools whenever a step requires computation."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[our_agent],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Answer the following user query, using the available arithmetic tools whenever a step requires computation: {query}"
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())