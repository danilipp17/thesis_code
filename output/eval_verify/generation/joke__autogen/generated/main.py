"""
Auto-generated AutoGen application: joke
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
        "You are a comedy writer. Take the previous joke and make it funnier by adding clever wordplay. Output 'IMPROVED' when done."
    ),
)

joke_polisher = AssistantAgent(
    name="Joke_Polisher",
    model_client=model_client,
    system_message=(
        "You are a storyteller. Add a surprising twist to the previous joke for the final polished version. Conclude with 'TERMINATE'."
    ),
)

# -- Team --

team = RoundRobinGroupChat(
    participants=[joke_generator, joke_improver, joke_polisher],
    max_turns=4,
)


async def main():
    stream = team.run_stream(
        task="Write a joke about cats, then improve and polish it."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())