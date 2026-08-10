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


model_client = OpenAIChatCompletionClient(model="gpt-4o")


# -- Agents --
analyze_meeting = AssistantAgent(
    name="analyze_meeting",
    model_client=model_client,
    system_message=(
        "You are an expert in analyzing meeting transcripts and summarizing "
        "the discussions into actionable tasks."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[analyze_meeting],
    termination_condition=termination,
)


async def main():
    # Load meeting transcript from file if available; otherwise use a small sample
    try:
        with open("meeting_notes.txt", "r") as f:
            transcript = f.read()
    except Exception:
        transcript = (
            "Team meeting discussing the upcoming product launch. "
            "Decisions made: finalize marketing plan by next Friday, "
            "assign Alice to prepare the press release, Bob to coordinate with design "
            "for final assets, and schedule a dry-run presentation on Tuesday."
        )

    prompt = (
        "You are an expert in analyzing meeting transcripts and summarizing "
        "the discussions into actionable tasks. Analyze the provided meeting "
        "transcript and generate a JSON list of "
        '{"name": str, "description": str} objects.\n\n'
        f"Transcript:\n{transcript}"
    )

    # Run the team with the concrete, interpolated prompt so the assistant
    # actually receives the transcript text (not a literal placeholder).
    stream = team.run_stream(task=prompt)

    # Console prints the interaction to stdout.
    await Console(stream)

    # Close the model client when done.
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
