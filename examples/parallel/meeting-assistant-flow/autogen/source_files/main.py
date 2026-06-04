"""
meeting-assistant — AutoGen v0.4 port of the CrewAI Flow original.

Original: examples/parallel/meeting-assistant-flow/crewai — a CrewAI Flow
with a single ``meeting_analyzer`` agent (Process.sequential, one task)
that turns a meeting transcript into a list of actionable tasks, then
fans out into Trello/CSV/Slack side effects.

AutoGen mapping:
  - single Crew agent -> single AssistantAgent
  - Process.sequential single-task crew -> RoundRobinGroupChat
    with ``max_turns=1`` (TurnLimitTermination(1))
  - the @start file-load and three @listen side effects of the original
    are not coordination-time concerns in AutoGen; they live as plain
    Python helpers around ``team.run`` (preserved as a thesis finding
    about side-effect representability).
"""

import csv

from dotenv import load_dotenv

load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

from tools import save_tasks_to_trello, send_message_to_channel


model_client = OpenAIChatCompletionClient(model="gpt-4o")

meeting_analyzer = AssistantAgent(
    name="meeting_analyzer",
    model_client=model_client,
    system_message=(
        "You are an expert in analyzing meeting transcripts and "
        "summarizing the discussions into actionable tasks. Your ability "
        "to identify important issues helps ensure teams can follow up "
        "and address key points effectively. Analyze the provided meeting "
        "transcript and generate a set of detailed, well-organized issues "
        "based on the discussion. Return the result as a JSON list of "
        '{"name": str, "description": str} objects.'
    ),
)

team = RoundRobinGroupChat(
    participants=[meeting_analyzer],
    max_turns=1,
)


async def main():
    with open("meeting_notes.txt", "r") as f:
        transcript = f.read()

    result = await Console(
        team.run_stream(
            task=(
                "Analyze the following meeting transcript and extract "
                "actionable tasks.\n\n"
                f"Transcript:\n{transcript}"
            )
        )
    )

    import json
    last = result.messages[-1].content
    try:
        tasks = json.loads(last)
    except Exception:
        tasks = []

    save_tasks_to_trello(tasks)
    with open("new_tasks.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Description"])
        for t in tasks:
            w.writerow([t.get("name", ""), t.get("description", "")])
    send_message_to_channel(
        f"{len(tasks)} New tasks have been added to Trello!"
    )

    await model_client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
