"""
Auto-generated LangGraph application: meeting_assistant_flow
"""

import dotenv
from typing import Annotated, List, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

import csv
import os

# Define MeetingTask so MeetingState can reference it
class MeetingTask(TypedDict):
    name: str
    description: str

class MeetingState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    tasks: List[MeetingTask]
    transcript: str

model = ChatOpenAI(model="gpt-4")


def load_meeting_notes(state: MeetingState) -> dict:
    """Subgraph node: load_meeting_notes"""
    print("Loading Meeting Notes")
    # If a transcript was provided in the incoming state, keep it.
    # Otherwise, try to read a meeting_notes.txt if present.
    transcript = state.get("transcript", "") or ""
    if not transcript:
        if os.path.exists("meeting_notes.txt"):
            with open("meeting_notes.txt", "r") as f:
                transcript = f.read()
                print("Loaded transcript from meeting_notes.txt")
        else:
            transcript = "No transcript provided."
            print("No transcript provided; using placeholder.")
    messages = [
        SystemMessage(content="Meeting Assistant initialized."),
        HumanMessage(content=f"Transcript loaded: {transcript[:500]}")
    ]
    return {"transcript": transcript, "messages": messages}


def generate_tasks_from_meeting_transcript(state: MeetingState) -> dict:
    """Subgraph node: generate_tasks_from_meeting_transcript"""
    print("Kickoff the Meeting Assistant Crew")
    transcript = state.get("transcript", "") or ""
    # Very small deterministic "analysis" to produce representative tasks.
    tasks: List[MeetingTask] = []

    # Simple heuristics to create tasks from transcript content
    if "follow up" in transcript.lower() or "follow-up" in transcript.lower():
        tasks.append(
            MeetingTask(
                name="Follow up on action items",
                description="Review the meeting transcript and follow up on the action items mentioned. Ensure owners are assigned and deadlines set."
            )
        )
    if "bug" in transcript.lower() or "issue" in transcript.lower():
        tasks.append(
            MeetingTask(
                name="Investigate reported issue",
                description="Investigate the reported bug/issue described in the meeting. Reproduce the issue, document steps to reproduce, and propose fixes."
            )
        )
    # Always add a generic summarization and planning task
    tasks.append(
        MeetingTask(
            name="Create meeting summary and next steps",
            description=f"Summarize the meeting and list next steps based on the transcript excerpt: \"{transcript[:200]}\""
        )
    )

    # If no real content was found, create a sample task to ensure downstream steps run
    if not tasks:
        tasks.append(
            MeetingTask(
                name="Identify action items",
                description="No explicit action items detected. Please review the meeting notes and identify any tasks that should be tracked."
            )
        )

    messages = [HumanMessage(content="Generated tasks from transcript.")]
    # Print the tasks for visibility in this run
    print("TASKS GENERATED:")
    for t in tasks:
        print(f"- {t['name']}: {t['description'][:120]}")

    return {"tasks": tasks, "messages": messages}


def add_tasks_to_trello(state: MeetingState) -> dict:
    """Node: add_tasks_to_trello"""
    print("Adding Tasks to Trello (simulated)")
    tasks = state.get("tasks", []) or []
    for idx, task in enumerate(tasks, start=1):
        print(f"Simulating Trello card creation #{idx}: {task['name']}")
    messages = [SystemMessage(content=f"Simulated adding {len(tasks)} tasks to Trello.")]
    return {"messages": messages}


def save_new_tasks_to_csv(state: MeetingState) -> dict:
    """Node: save_new_tasks_to_csv"""
    print("Saving New Tasks to CSV")
    tasks = state.get("tasks", []) or []
    filename = "new_tasks.csv"
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Description"])
        for task in tasks:
            writer.writerow([task["name"], task["description"]])
    print(f"Wrote {len(tasks)} tasks to {filename}")
    messages = [SystemMessage(content=f"Wrote {len(tasks)} tasks to {filename}")]
    return {"messages": messages}


def send_slack_notification(state: MeetingState) -> dict:
    """Node: send_slack_notification"""
    print("Sending Slack Notification (simulated)")
    tasks = state.get("tasks", []) or []
    message = f"{len(tasks)} New tasks have been added to Trello!"
    # Simulate sending by printing
    print("Slack message:", message)
    messages = [SystemMessage(content=message)]
    return {"messages": messages}


# Build the graph
graph = StateGraph(MeetingState)

graph.add_node("load_meeting_notes", load_meeting_notes)
graph.add_node("generate_tasks_from_meeting_transcript", generate_tasks_from_meeting_transcript)
graph.add_node("add_tasks_to_trello", add_tasks_to_trello)
graph.add_node("save_new_tasks_to_csv", save_new_tasks_to_csv)
graph.add_node("send_slack_notification", send_slack_notification)

graph.add_edge(START, "load_meeting_notes")
graph.add_edge("load_meeting_notes", "generate_tasks_from_meeting_transcript")

# After generating tasks, run three parallel sinks
graph.add_edge("generate_tasks_from_meeting_transcript", "add_tasks_to_trello")
graph.add_edge("generate_tasks_from_meeting_transcript", "save_new_tasks_to_csv")
graph.add_edge("generate_tasks_from_meeting_transcript", "send_slack_notification")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    # Provide a representative concrete input
    initial_state = {
        "messages": [HumanMessage(content="Start the task.")],
        "tasks": [],
        "transcript": "We need to follow up on the API bug reported last week. Also, please schedule a follow up meeting to discuss deployment."
    }
    result = app.invoke(initial_state)
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
