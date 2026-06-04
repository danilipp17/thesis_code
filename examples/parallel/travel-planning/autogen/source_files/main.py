"""
Travel Planning — AutoGen v0.4 implementation.

A team of four agents collaborates on a travel plan: a planner sketches the
itinerary, a local agent suggests authentic activities, a language agent
contributes communication tips, and a summary agent integrates everything
into the final plan. The team is coordinated by a SelectorGroupChat that
routes each turn to the most appropriate participant, and terminates when
the summary agent emits the TERMINATE keyword.

Source: AutoGen AgentChat tutorial — "Travel Planning".
"""

from dotenv import load_dotenv

load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# -- LLM client --
model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Agents --
planner_agent = AssistantAgent(
    "planner_agent",
    model_client=model_client,
    description="A helpful assistant that can plan trips.",
    system_message=(
        "You are a helpful assistant that can suggest a travel plan for a "
        "user based on their request."
    ),
)

local_agent = AssistantAgent(
    "local_agent",
    model_client=model_client,
    description="A local assistant that can suggest local activities or places to visit.",
    system_message=(
        "You are a helpful assistant that can suggest authentic and "
        "interesting local activities or places to visit for a user and "
        "can utilize any context information provided."
    ),
)

language_agent = AssistantAgent(
    "language_agent",
    model_client=model_client,
    description="A helpful assistant that can provide language tips for a given destination.",
    system_message=(
        "You are a helpful assistant that can review travel plans, "
        "providing feedback on important/critical tips about how best to "
        "address language or communication challenges for the given "
        "destination. If the plan already includes language tips, you can "
        "mention that the plan is satisfactory, with rationale."
    ),
)

travel_summary_agent = AssistantAgent(
    "travel_summary_agent",
    model_client=model_client,
    description="An assistant that can summarize the travel plan.",
    system_message=(
        "You are a helpful assistant that can take in all of the "
        "suggestions and advice from the other agents and provide a "
        "detailed final travel plan. You must ensure that the final plan "
        "is integrated and complete. YOUR FINAL RESPONSE MUST BE THE "
        "COMPLETE PLAN. When the plan is complete and all perspectives "
        "are integrated, you can respond with TERMINATE."
    ),
)

# -- Team --
termination = TextMentionTermination("TERMINATE")
group_chat = SelectorGroupChat(
    [planner_agent, local_agent, language_agent, travel_summary_agent],
    model_client=model_client,
    termination_condition=termination,
)


async def main():
    await Console(group_chat.run_stream(task="Plan a 10 day trip to Luxembourg."))
    await model_client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
