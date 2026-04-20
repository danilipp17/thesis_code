"""
Auto-generated AutoGen application: AI_News_System
"""

import asyncio
import dotenv

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_core.tools import FunctionTool
from tools import web_search

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
web_search_tool = FunctionTool(
    web_search,
    description="Search the web for recent events and news",
)

# -- Agents --
researcher = AssistantAgent(
    name="Investigative_Reporter",
    model_client=model_client,
    tools=[web_search_tool],
    system_message=(
        "Find the most interesting facts about a given topic. You are a veteran reporter known for deep dives."
    ),
)

writer = AssistantAgent(
    name="Creative_Editor",
    model_client=model_client,
    system_message=(
        "Write a compelling story based on facts. You turn dry facts into captivating narratives."
    ),
)

# -- Team --
termination = MaxMessageTermination(10) | TextMentionTermination("TERMINATE")

team = RoundRobinGroupChat(
    participants=[researcher, writer],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Draft an article based on the research."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())