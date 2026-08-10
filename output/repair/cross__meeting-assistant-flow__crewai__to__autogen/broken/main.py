"""
Auto-generated AutoGen application: meeting_assistant_flow
"""

import asyncio
import dotenv
from typing import Any, Dict, List, Optional

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


model_client = OpenAIChatCompletionClient(model="gpt-4")


# -- Agents --
meeting_analyzer = AssistantAgent(
    name="Meeting_Transcript_Analysis_Agent",
    model_client=model_client,
    system_message=(
        "Analyze the provided meeting transcript and extract important, actionable tasks or issues.  The goal is to break down the meeting content into well-structured,  detailed issues that can be easily understood and uploaded to Trello.\nHere is the meeting transcript for your reference:\\n\\n {transcript} You are an expert in analyzing meeting transcripts and summarizing the discussions into actionable tasks.  Your ability to identify important issues helps ensure teams can follow up and address key points effectively."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[meeting_analyzer],
    termination_condition=termination,
)


async def main():
    stream = team.run_stream(
        task="Analyze the provided meeting transcript and generate a set of detailed,  well-organized issues based on the discussion. Focus on breaking down the transcript into manageable tasks or issues,  making sure to document each issue thoroughly with steps to reproduce, acceptance criteria,  and any other relevant details.\nHere is the meeting transcript for your reference:\\n\\n {transcript}"
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())