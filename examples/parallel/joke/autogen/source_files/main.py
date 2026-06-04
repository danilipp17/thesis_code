"""
joke — AutoGen port of the LangGraph original.

Original: examples/langgraph/joke/joke.py — three-step refinement
(generate → conditional skip-or-improve → polish) using StateGraph.

AutoGen mapping:
  - StateGraph         -> RoundRobinGroupChat over 3 AssistantAgents
  - TypedDict State    -> conversation messages (implicit AutoGen state)
  - add_node           -> AssistantAgent participants
  - linear edges       -> round-robin participant order
  - conditional gate   -> NOT directly representable in RoundRobin;
                          all three agents always run. This loss is
                          itself a finding about framework expressivity.
"""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv()

model_client = OpenAIChatCompletionClient(
    model="gpt-4o",
    api_key=os.environ.get("OPENAI_API_KEY"),
)

joke_generator = AssistantAgent(
    name="Joke_Generator",
    model_client=model_client,
    system_message=(
        "You are a witty comedian. Write a short joke about the requested topic."
    ),
)

joke_improver = AssistantAgent(
    name="Joke_Improver",
    model_client=model_client,
    system_message=(
        "You are a comedy writer. Take the previous joke and make it funnier by "
        "adding clever wordplay. Output 'IMPROVED' when done."
    ),
)

joke_polisher = AssistantAgent(
    name="Joke_Polisher",
    model_client=model_client,
    system_message=(
        "You are a storyteller. Add a surprising twist to the previous joke for "
        "the final polished version. Conclude with 'TERMINATE'."
    ),
)

termination = MaxMessageTermination(max_messages=4)

team = RoundRobinGroupChat(
    participants=[joke_generator, joke_improver, joke_polisher],
    termination_condition=termination,
)


async def main():
    print("Starting AutoGen Joke Generation...")
    result = await team.run(
        task="Write a joke about cats, then improve and polish it."
    )
    for msg in result.messages:
        print(f"[{msg.source}]: {msg.content}")


if __name__ == "__main__":
    asyncio.run(main())
