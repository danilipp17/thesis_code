"""
Auto-generated AutoGen application: meeting_assistant_flow
"""

import asyncio
import dotenv
import os
from typing import Any, Dict, List, Optional

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


model_client = OpenAIChatCompletionClient(model="gpt-4")


# -- Agents --
# Keep system message focused on role/backstory; the transcript will be provided
# at runtime when kicking off the team so it is not hardcoded into the agent.
meeting_analyzer = AssistantAgent(
    name="Meeting_Transcript_Analysis_Agent",
    model_client=model_client,
    system_message=(
        "You are an expert in analyzing meeting transcripts and summarizing the discussions into "
        "actionable tasks. Your ability to identify important issues helps ensure teams can follow "
        "up and address key points effectively. Analyze the transcript provided by the user and "
        "produce a JSON list of issues with titles and bodies, containing clear instructions, steps "
        "to reproduce, and acceptance criteria where applicable."
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
    # Load the meeting transcript from a file if available, otherwise use a short fallback.
    transcript = "Meeting transcript goes here."
    try:
        with open("meeting_notes.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                transcript = content
    except FileNotFoundError:
        # Fall back but still let the model do the work (do not hardcode results).
        transcript = (
            "Attendees discussed improving the dashboard mobile responsiveness, adding a token "
            "count progress indicator, and delegating testing to the frontend team. Deadline for "
            "the token indicator is next sprint. Action item: frontend to prepare a design spec."
        )

    task_prompt = (
        "Analyze the provided meeting transcript and generate a set of detailed, well-organized "
        "issues based on the discussion. Focus on breaking down the transcript into manageable "
        "tasks or issues, making sure to document each issue thoroughly with steps to reproduce, "
        "acceptance criteria, and any other relevant details.\n\n"
        "Here is the meeting transcript for your reference:\n\n"
        f"{transcript}"
    )

    stream = team.run_stream(task=task_prompt)
    # Console will stream model outputs to stdout. This ensures the result is produced at runtime
    # by the autogen framework and the language model.
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
