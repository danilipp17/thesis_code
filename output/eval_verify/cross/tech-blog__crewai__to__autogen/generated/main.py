"""
Auto-generated AutoGen application: tech_blog
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
researcher = AssistantAgent(
    name="Senior_Tech_Researcher",
    model_client=model_client,
    system_message=(
        "Gather comprehensive, up-to-date information on '{topic}'. An expert researcher skilled at finding the latest technological trends and summarizing them clearly."
    ),
)

writer = AssistantAgent(
    name="Tech_Blog_Writer",
    model_client=model_client,
    system_message=(
        "Write an engaging, easy-to-read blog post based on research. A seasoned technical writer who can make complex topics accessible to a broad audience."
    ),
)

editor = AssistantAgent(
    name="Content_Editor",
    model_client=model_client,
    system_message=(
        "Review and refine the blog post for clarity, grammar, and flow. A meticulous editor with a keen eye for detail, ensuring every published piece is top-notch."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[researcher, writer, editor],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Conduct thorough research on the topic: '{topic}'. Identify key trends, benefits, challenges, and future outlook."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())