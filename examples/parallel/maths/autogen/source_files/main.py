"""
react — AutoGen v0.4 port of the LangGraph original.

Original: examples/parallel/react/langgraph — a single agent in a
ReAct loop with three arithmetic tools (add, subtract, multiply) and a
conditional edge that exits when no more tool calls are requested.

AutoGen mapping:
  - LangGraph agent node       -> AssistantAgent (the ReAct loop is
                                  the agent's internal behaviour)
  - LangGraph @tool primitives -> FunctionTool wrappers
  - StateGraph conditional gate
    (continue/end)              -> AutoGen agents end their turn when
                                  no tool call is emitted; a single-
                                  member RoundRobinGroupChat with
                                  ``max_turns=1`` keeps the loop scoped
                                  to one user query.
"""

from dotenv import load_dotenv

load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient


def add(a: int, b: int) -> int:
    """This is an addition function that adds 2 numbers together."""
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtraction function."""
    return a - b


def multiply(a: int, b: int) -> int:
    """Multiplication function."""
    return a * b


add_tool = FunctionTool(add, description="Add two integers.")
subtract_tool = FunctionTool(subtract, description="Subtract two integers.")
multiply_tool = FunctionTool(multiply, description="Multiply two integers.")

model_client = OpenAIChatCompletionClient(model="gpt-4o")

our_agent = AssistantAgent(
    name="our_agent",
    model_client=model_client,
    tools=[add_tool, subtract_tool, multiply_tool],
    system_message=(
        "You are my AI assistant, please answer my query to the best of "
        "your ability."
    ),
    reflect_on_tool_use=True,
)

team = RoundRobinGroupChat(participants=[our_agent], max_turns=1)


async def main():
    await Console(
        team.run_stream(
            task=(
                "Add 40 + 12 and then multiply the result by 6. Also tell "
                "me a joke please."
            )
        )
    )
    await model_client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
