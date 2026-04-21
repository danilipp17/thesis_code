"""
Auto-generated AutoGen application: content_pipeline
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
from tools import web_search, word_count

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
web_search_tool = FunctionTool(
    web_search,
    description="Search the web for information on a given query.",
)
word_count_tool = FunctionTool(
    word_count,
    description="Counts the number of words in a given text.",
)

# -- Agents --
content_writer = AssistantAgent(
    name="Content_Writer",
    model_client=model_client,
    tools=[word_count_tool],
    system_message=(
        "You are a seasoned content writer. Using the research findings from the previous agent, write a comprehensive article of 800-1200 words. Include an engaging introduction, clear section headings, and a conclusion with key takeaways. Use the word count tool to verify length."
    ),
)

quality_reviewer = AssistantAgent(
    name="Quality_Reviewer",
    model_client=model_client,
    tools=[word_count_tool],
    system_message=(
        "You are a meticulous editor. Review the article for factual accuracy, grammar, style, and completeness. Provide a quality score (1-10), a list of issues found, and specific suggestions for improvement. When done, reply with TERMINATE."
    ),
)

research_analyst = AssistantAgent(
    name="Research_Analyst",
    model_client=model_client,
    tools=[web_search_tool],
    system_message=(
        "You are an experienced research analyst with a background in investigative journalism. Research the given topic thoroughly using your web search tool. Find at least 3 reliable sources and compile key facts, statistics, and expert opinions. Structure your findings as bullet points grouped by subtopic."
    ),
)

# -- Team --
termination = MaxMessageTermination(3)

team = RoundRobinGroupChat(
    participants=[content_writer, quality_reviewer, research_analyst],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Write an article about the future of renewable energy in 2026."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())