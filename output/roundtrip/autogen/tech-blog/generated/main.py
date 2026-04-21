"""
Auto-generated AutoGen application: tech_blog
"""

import asyncio
import dotenv

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


model_client = OpenAIChatCompletionClient(model="gpt-4o")


# -- Agents --
editor = AssistantAgent(
    name="Editor",
    model_client=model_client,
    system_message=(
        "You are a Content Editor. Review the blog post written by the Writer. Fix grammar, improve flow, and output the final polished version. Conclude with 'TERMINATE'."
    ),
)

researcher = AssistantAgent(
    name="Researcher",
    model_client=model_client,
    system_message=(
        "You are a Senior Tech Researcher. Your goal is to gather comprehensive information on the requested topic and provide a detailed summary of your findings."
    ),
)

writer = AssistantAgent(
    name="Writer",
    model_client=model_client,
    system_message=(
        "You are a Tech Blog Writer. Take the research provided by the Researcher and write a clear, engaging 500-word blog post. Output 'WRITTEN' when done."
    ),
)

# -- Team --
termination = MaxMessageTermination(4)

team = RoundRobinGroupChat(
    participants=[editor, researcher, writer],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="We need a blog post about Agentic AI Frameworks. Please research, write, and edit."
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())