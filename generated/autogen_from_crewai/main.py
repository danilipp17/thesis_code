"""
Auto-generated AutoGen application: AcademicResearchFlow
"""

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_core.tools import FunctionTool
from tools import academic_search_tool

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
academic_search_tool_tool = FunctionTool(
    academic_search_tool,
    description="Search academic papers and journals to find relevant literature.",
)

# -- Agents --
manager_academic_research_crew = AssistantAgent(
    name="Manager",
    model_client=model_client,
    system_message=(
        ""
    ),
)

prof_writer = AssistantAgent(
    name="Academic Writer and Editor",
    model_client=model_client,
    system_message=(
        "Take rough notes and outlines to produce a formal, peer-review-ready academic paper. You have published in top-tier journals and know exactly how to structure an academic paper for maximum impact and clarity."
    ),
)

senior_researcher = AssistantAgent(
    name="Senior Academic Researcher",
    model_client=model_client,
    tools=[academic_search_tool_tool],
    system_message=(
        "Conduct extensive literature reviews and gather empirical data on the chosen topic. You are a tenured professor with years of experience navigating complex academic databases and synthesizing information."
    ),
)

# -- Team --
team = SelectorGroupChat(
    participants=[manager_academic_research_crew, prof_writer, senior_researcher],
    model_client=model_client,
)


async def main():
    stream = team.run_stream(
        task="Start the task."  # TODO: provide initial message
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())