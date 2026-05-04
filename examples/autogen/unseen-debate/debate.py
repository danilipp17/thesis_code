"""
Unseen example: A structured debate system using AutoGen.
This example was NOT used during development of the OSCIN parsers.
It tests: SelectorGroupChat, multiple agents with different roles,
composite termination (| operator), and tool usage.
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import (
    MaxMessageTermination,
    TextMentionTermination,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.tools import FunctionTool


# --- Tools ---

def fact_check(claim: str) -> str:
    """Verify a factual claim and return evidence."""
    return f"Fact check for '{claim}': verified with moderate confidence."


def cite_source(topic: str, year: int) -> str:
    """Find and cite an academic source on a topic."""
    return f"Source: '{topic}' - Journal of AI Research, {year}."


fact_check_tool = FunctionTool(fact_check, description="Verify factual claims")
cite_tool = FunctionTool(cite_source, description="Find academic citations")


# --- Model ---

model_client = OpenAIChatCompletionClient(model="gpt-4o")


# --- Agents ---

moderator = AssistantAgent(
    name="moderator",
    system_message="You are a debate moderator. Guide the discussion, ensure fair turn-taking, and summarize key points. When the debate has reached a conclusion, say DEBATE_COMPLETE.",
    model_client=model_client,
    description="Moderates the debate and ensures productive discussion.",
)

proponent = AssistantAgent(
    name="proponent",
    system_message="You argue IN FAVOR of the given proposition. Use evidence, logical reasoning, and persuasive rhetoric. Always cite sources when making factual claims.",
    model_client=model_client,
    tools=[fact_check_tool, cite_tool],
    description="Argues in favor of the proposition with evidence.",
)

opponent = AssistantAgent(
    name="opponent",
    system_message="You argue AGAINST the given proposition. Challenge assumptions, present counterarguments, and identify logical fallacies.",
    model_client=model_client,
    tools=[fact_check_tool],
    description="Argues against the proposition with counterarguments.",
)

judge = AssistantAgent(
    name="judge",
    system_message="You are an impartial judge. After hearing both sides, evaluate the strength of arguments and declare a winner. Be specific about which arguments were strongest.",
    model_client=model_client,
    description="Evaluates arguments and declares the debate winner.",
)


# --- Team ---

termination = MaxMessageTermination(max_messages=20) | TextMentionTermination("DEBATE_COMPLETE")

debate_team = SelectorGroupChat(
    participants=[moderator, proponent, opponent, judge],
    model_client=model_client,
    termination_condition=termination,
)


# --- Run ---

async def main():
    result = await debate_team.run(
        task="Debate the proposition: 'Artificial General Intelligence will be achieved within the next 10 years.'"
    )
    print(result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
