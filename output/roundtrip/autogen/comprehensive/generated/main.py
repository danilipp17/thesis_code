"""
Auto-generated AutoGen application: comprehensive
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
from tools import calculate_tax, db_lookup

model_client = OpenAIChatCompletionClient(model="gpt-4")

# -- Tools --
calculate_tax_tool = FunctionTool(
    calculate_tax,
    description="Calculates standard tax rate.",
)
db_lookup_tool = FunctionTool(
    db_lookup,
    description="Looks up database records.",
)

# -- Agents --
admin = AssistantAgent(
    name="Admin",
    model_client=model_client,
    system_message=(
        "A human admin overseeing the group."
    ),
)

analyst = AssistantAgent(
    name="Analyst",
    model_client=model_client,
    system_message=(
        "You analyze data. Tax calculations are your specialty."
    ),
)

researcher = AssistantAgent(
    name="Researcher",
    model_client=model_client,
    system_message=(
        "You are a data researcher. Find relevant information."
    ),
)

# -- Team --
termination = MaxMessageTermination(15) | TextMentionTermination("TERMINATE")

team = RoundRobinGroupChat(
    participants=[admin, analyst, researcher],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Start the task."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())