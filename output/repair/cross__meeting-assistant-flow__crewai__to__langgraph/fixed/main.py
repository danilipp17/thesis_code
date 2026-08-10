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

import json
import os

# Define MeetingTask so the TypedDict reference is valid
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
    # Read meeting notes from file if present, otherwise use a small default transcript.
    transcript_path = "meeting_notes.txt"
    if os.path.exists(transcript_path):
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()
    else:
        transcript = (
            "Project kickoff meeting. Discussed roadmap, assigned action items: "
            "1) Integrate analytics dashboard by next sprint. 2) Review mobile layout. "
            "3) Follow up with design on token counter."
        )

    # Create an initial message indicating the transcript was loaded.
    init_message = HumanMessage(content=f"Loaded transcript ({len(transcript)} chars).")
    return {"transcript": transcript, "messages": [init_message], "tasks": []}


def generate_tasks_from_meeting_transcript(state: MeetingState) -> dict:
    """Subgraph node: generate_tasks_from_meeting_transcript"""
    transcript = state.get("transcript", "")
    # Build a prompt asking the LLM to produce a JSON list of tasks with 'name' and 'description'.
    system_text = (
        "You are a Meeting Transcript Analysis Agent. Analyze the provided meeting transcript and "
        "extract important, actionable tasks or issues. Output ONLY a JSON array of objects, each "
        "with the keys 'name' and 'description'. The 'name' should be a short title, and the "
        "'description' should provide clear steps, acceptance criteria or relevant details."
    )
    human_text = f"Here is the meeting transcript:\n\n{transcript}\n\nPlease produce the JSON list as described."

    messages = [SystemMessage(content=system_text), HumanMessage(content=human_text)]
    response = model.invoke(messages)

    # Extract text content from the model response
    if hasattr(response, "content"):
        text = response.content
    else:
        text = str(response)

    tasks = []
    # Try to parse JSON from the model output. If parsing fails, keep the raw output as one task description.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("title") or item.get("task") or "Untitled Task"
                    description = item.get("description") or item.get("body") or item.get("details") or ""
                    tasks.append({"name": str(name), "description": str(description)})
        else:
            # If model returned an object, try to extract reasonable fields
            if isinstance(parsed, dict):
                name = parsed.get("name", "Meeting Task")
                description = json.dumps(parsed)
                tasks.append({"name": str(name), "description": description})
            else:
                tasks.append({"name": "Model Output", "description": str(parsed)})
    except Exception:
        # Fallback: include the raw generated text as one task description
        tasks.append({"name": "Model Output", "description": text})

    # Return both the raw model message (for downstream nodes that expect messages) and parsed tasks
    return {"messages": [response], "tasks": tasks, "transcript": transcript}


def add_tasks_to_trello(state: MeetingState) -> dict:
    """Node: add_tasks_to_trello"""
    tasks = state.get("tasks", [])
    if not tasks:
        print("No tasks to add to Trello.")
    else:
        for t in tasks:
            name = t.get("name", "<no name>")
            desc = t.get("description", "")
            # Here we print what would be sent to Trello (external API calls are not performed in this demo).
            print(f"[TRELLO] Create card: {name}\nDescription: {desc}\n---")
    # Preserve messages and tasks in state
    return {"messages": state.get("messages", []), "tasks": tasks, "transcript": state.get("transcript", "")}


def save_new_tasks_to_csv(state: MeetingState) -> dict:
    """Node: save_new_tasks_to_csv"""
    tasks = state.get("tasks", [])
    csv_path = "new_tasks.csv"
    try:
        import csv

        with open(csv_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Name", "Description"])
            for task in tasks:
                writer.writerow([task.get("name", ""), task.get("description", "")])
        print(f"Saved {len(tasks)} tasks to {csv_path}")
    except Exception as e:
        print("Failed to save tasks to CSV:", e)
    return {"messages": state.get("messages", []), "tasks": tasks, "transcript": state.get("transcript", "")}


def send_slack_notification(state: MeetingState) -> dict:
    """Node: send_slack_notification"""
    tasks = state.get("tasks", [])
    count = len(tasks)
    # Use the model to generate a friendly Slack notification message so the result is produced at runtime.
    system_text = "You are a helpful assistant that drafts short Slack notifications."
    human_text = f"Draft a short Slack message announcing that {count} new tasks were added to Trello. Keep it concise and friendly."

    messages = [SystemMessage(content=system_text), HumanMessage(content=human_text)]
    response = model.invoke(messages)
    if hasattr(response, "content"):
        slack_message = response.content
    else:
        slack_message = str(response)

    # Print the generated Slack message (in lieu of sending via Slack API).
    print("[SLACK] Message to channel:")
    print(slack_message)
    return {"messages": [response], "tasks": tasks, "transcript": state.get("transcript", "")}


# Build the graph
graph = StateGraph(MeetingState)

graph.add_node("load_meeting_notes", load_meeting_notes)
graph.add_node("generate_tasks_from_meeting_transcript", generate_tasks_from_meeting_transcript)
graph.add_node("add_tasks_to_trello", add_tasks_to_trello)
graph.add_node("save_new_tasks_to_csv", save_new_tasks_to_csv)
graph.add_node("send_slack_notification", send_slack_notification)

graph.add_edge(START, "load_meeting_notes")
graph.add_edge("load_meeting_notes", "generate_tasks_from_meeting_transcript")

# Wire the generate step to the three sink steps (they run after generation)
graph.add_edge("generate_tasks_from_meeting_transcript", "add_tasks_to_trello")
graph.add_edge("generate_tasks_from_meeting_transcript", "save_new_tasks_to_csv")
graph.add_edge("generate_tasks_from_meeting_transcript", "send_slack_notification")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "tasks": [], "transcript": "sample transcript"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
