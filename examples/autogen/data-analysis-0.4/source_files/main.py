import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    # 1. Define LLM Client
    model_client_gpt4o = OpenAIChatCompletionClient(
        model="gpt-4o",
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=0.2
    )

    model_client_mini = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=0
    )

    # 2. Define Tools
    def fetch_weather(location: str) -> str:
        """Fetch the current weather for a specific location."""
        return f"The weather in {location} is 72F and sunny."

    def calculate_travel_time(distance: int) -> str:
        """Calculate travel time based on distance in miles."""
        return f"Estimated time: {distance / 60} hours."

    # 3. Initialize Agents using AutoGen 0.4 API
    travel_planner = AssistantAgent(
        name="Travel_Planner",
        model_client=model_client_gpt4o,
        system_message="You are a travel planner. You organize itineraries and schedule events.",
        tools=[fetch_weather, calculate_travel_time]
    )

    local_guide = AssistantAgent(
        name="Local_Guide",
        model_client=model_client_mini,
        system_message="You provide local recommendations for restaurants and sights."
    )

    budget_reviewer = AssistantAgent(
        name="Budget_Reviewer",
        model_client=model_client_mini,
        system_message="You review the proposed itinerary to ensure it stays under budget."
    )

    # 4. Define Orchestration
    # AutoGen 0.4 uses explicit termination conditions and routing teams
    termination = MaxMessageTermination(max_messages=8)
    
    # AutoGen 0.4 replaces GroupChat with specific Team variants
    team = RoundRobinGroupChat(
        participants=[travel_planner, local_guide, budget_reviewer],
        termination_condition=termination
    )

    # 5. Execute Flow
    print("Starting AutoGen 0.4 Flow...")
    result = await team.run(task="Create a 3-day itinerary for a weekend trip to Austin, TX.")
    
    # Optional: Print messages
    for msg in result.messages:
        print(f"[{msg.source}]: {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())
