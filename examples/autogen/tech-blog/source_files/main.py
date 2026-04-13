import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(
    model="gpt-4o",
    api_key=os.environ.get("OPENAI_API_KEY"),
)

researcher = AssistantAgent(
    name="Researcher",
    model_client=model_client,
    system_message="You are a Senior Tech Researcher. Your goal is to gather comprehensive information on the requested topic and provide a detailed summary of your findings.",
)

writer = AssistantAgent(
    name="Writer",
    model_client=model_client,
    system_message="You are a Tech Blog Writer. Take the research provided by the Researcher and write a clear, engaging 500-word blog post. Output 'WRITTEN' when done.",
)

editor = AssistantAgent(
    name="Editor",
    model_client=model_client,
    system_message="You are a Content Editor. Review the blog post written by the Writer. Fix grammar, improve flow, and output the final polished version. Conclude with 'TERMINATE'.",
)

termination = MaxMessageTermination(max_messages=4)

team = RoundRobinGroupChat(
    participants=[researcher, writer, editor], termination_condition=termination
)


async def main():
    print("Starting AutoGen Tech Blog Generation...")
    result = await team.run(
        task="We need a blog post about Agentic AI Frameworks. Please research, write, and edit."
    )

    for msg in result.messages:
        print(f"[{msg.source}]: {msg.content}")


if __name__ == "__main__":
    asyncio.run(main())
