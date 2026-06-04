"""
meeting-assistant — LangGraph port of the CrewAI Flow original.

Original: examples/parallel/meeting-assistant-flow/crewai — a CrewAI Flow
that loads a meeting transcript, extracts actionable tasks via a single
LLM analyzer, and then fans out into three side-effect listeners
(Trello upload, CSV write, Slack notification).

LangGraph mapping:
  - MeetingState (Pydantic) -> TypedDict CodeReviewState
  - @start load_meeting_notes -> entry node ``load_meeting_notes``
  - @listen analyze step      -> node ``analyze_meeting`` (LLM call)
  - 3 parallel @listen sinks  -> 3 sequential trailing nodes
                                 (``upload_trello``, ``save_csv``,
                                  ``notify_slack``); LangGraph supports
                                 fan-out, but modelling them as a
                                 sequential tail keeps the topology
                                 trivially comparable across ports.
"""

import csv
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from tools import save_tasks_to_trello, send_message_to_channel

load_dotenv()

llm = ChatOpenAI(model="gpt-4o")


class MeetingState(TypedDict):
    transcript: str
    tasks: list[dict]


def load_meeting_notes(state: MeetingState) -> MeetingState:
    """Read the meeting transcript from disk."""
    with open("meeting_notes.txt", "r") as f:
        return {"transcript": f.read()}


def analyze_meeting(state: MeetingState) -> MeetingState:
    """LLM call extracting actionable tasks from the transcript."""
    prompt = (
        "You are an expert in analyzing meeting transcripts and summarizing "
        "the discussions into actionable tasks. Analyze the provided meeting "
        "transcript and generate a set of detailed, well-organized issues "
        "based on the discussion. Return a JSON list of "
        '{"name": str, "description": str} objects.\n\n'
        f"Transcript:\n{state['transcript']}"
    )
    response = llm.invoke(prompt)
    import json
    try:
        tasks = json.loads(response.content)
    except Exception:
        tasks = []
    return {"tasks": tasks}


def upload_trello(state: MeetingState) -> MeetingState:
    save_tasks_to_trello(state["tasks"])
    return {}


def save_csv(state: MeetingState) -> MeetingState:
    with open("new_tasks.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Description"])
        for t in state["tasks"]:
            w.writerow([t.get("name", ""), t.get("description", "")])
    return {}


def notify_slack(state: MeetingState) -> MeetingState:
    send_message_to_channel(
        f"{len(state['tasks'])} New tasks have been added to Trello!"
    )
    return {}


workflow = StateGraph(MeetingState)
workflow.add_node("load_meeting_notes", load_meeting_notes)
workflow.add_node("analyze_meeting", analyze_meeting)
workflow.add_node("upload_trello", upload_trello)
workflow.add_node("save_csv", save_csv)
workflow.add_node("notify_slack", notify_slack)

workflow.add_edge(START, "load_meeting_notes")
workflow.add_edge("load_meeting_notes", "analyze_meeting")
workflow.add_edge("analyze_meeting", "upload_trello")
workflow.add_edge("upload_trello", "save_csv")
workflow.add_edge("save_csv", "notify_slack")
workflow.add_edge("notify_slack", END)

app = workflow.compile()


if __name__ == "__main__":
    app.invoke({"transcript": "", "tasks": []})
