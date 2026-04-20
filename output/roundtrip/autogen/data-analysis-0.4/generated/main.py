"""
Auto-generated AutoGen application: data_analysis_0.4
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
from tools import calculate_travel_time, fetch_weather

model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# -- Tools --
calculate_travel_time_tool = FunctionTool(
    calculate_travel_time,
    description="Calculate travel time based on distance in miles.",
)
fetch_weather_tool = FunctionTool(
    fetch_weather,
    description="Fetch the current weather for a specific location.",
)

# -- Agents --
budget_reviewer = AssistantAgent(
    name="Budget_Reviewer",
    model_client=model_client,
    system_message=(
        "You review the proposed itinerary to ensure it stays under budget."
    ),
)

local_guide = AssistantAgent(
    name="Local_Guide",
    model_client=model_client,
    system_message=(
        "You provide local recommendations for restaurants and sights."
    ),
)

travel_planner = AssistantAgent(
    name="Travel_Planner",
    model_client=model_client,
    tools=[calculate_travel_time_tool, fetch_weather_tool],
    system_message=(
        "You are a travel planner. You organize itineraries and schedule events."
    ),
)

# -- Team --
termination = MaxMessageTermination(10) | TextMentionTermination("TERMINATE")

team = RoundRobinGroupChat(
    participants=[budget_reviewer, local_guide, travel_planner],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Create a 3-day itinerary for a weekend trip to Austin, TX."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())