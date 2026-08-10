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
        "Write a short joke on the given topic. A witty comedian who comes up with sharp, short jokes."
    ),
)

joke_improver = AssistantAgent(
    name="Joke_Improver",
    model_client=model_client,
    system_message=(
        "Improve a joke by adding clever wordplay. A seasoned writer who polishes jokes for punch."
    ),
)

joke_polisher = AssistantAgent(
    name="Joke_Polisher",
    model_client=model_client,
    system_message=(
        "Add a surprising twist to a joke. A storyteller who knows how to twist endings for effect."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[joke_generator],
    termination_condition=termination,
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[joke_improver],
    termination_condition=termination,
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[joke_polisher],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Write a short joke about {topic}."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())