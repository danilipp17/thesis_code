"""
Auto-generated LangGraph application: meeting_assistant_flow
"""

import dotenv
from typing import Annotated, TypedDict
import json
import os

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools import save_tasks_to_trello, send_message_to_channel
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [save_tasks_to_trello, send_message_to_channel]
tool_node = ToolNode(tools)


def run_team(state: State) -> dict:
    """Subgraph node: run_team

    This node reads a meeting transcript (from 'meeting_notes.txt' if present,
    otherwise uses a fallback sample), extracts simple actionable tasks, calls
    the side-effect helpers, and returns a messages list containing the JSON
    serialized tasks as the last message (so the caller can print or consume it).
    """
    # Try to obtain transcript from a file; fall back to a sample if missing.
    transcript = ""
    try:
        if os.path.exists("meeting_notes.txt"):
            with open("meeting_notes.txt", "r", encoding="utf-8") as f:
                transcript = f.read().strip()
    except Exception:
        transcript = ""

    if not transcript:
        transcript = (
            "Team retro:\n"
            "- Alice: We should improve onboarding documentation.\n"
            "- Bob: The deployment pipeline failed twice this week.\n"
            "- Carol: Consider adding more integration tests.\n\n"
            "Decisions: prioritize onboarding and stabilize CI.\n"
            "Action: Alice to draft onboarding doc. Bob to investigate CI flakiness."
        )

    # Simple extraction heuristics: lines that start with "- " or "Action:" or "Actions:"
    tasks = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            text = line[2:].strip()
            name = text.split(":")[0] if ":" in text else (text[:50] + "..." if len(text) > 50 else text)
            description = text
            tasks.append({"name": name, "description": description})
        elif line.lower().startswith("action:") or line.lower().startswith("actions:"):
            # Could contain multiple comma-separated directives; split by '.' or ';'
            rest = line.split(":", 1)[1].strip() if ":" in line else line
            parts = [p.strip() for p in rest.replace(";", ".").split(".") if p.strip()]
            for p in parts:
                name = p.split(" to ")[0][:60]
                tasks.append({"name": name, "description": p})

    # If no explicit items found, fall back to first two sentences as tasks.
    if not tasks:
        # split into sentences rudimentarily
        sentences = [s.strip() for s in transcript.replace("\n", " ").split(".") if s.strip()]
        for i, s in enumerate(sentences[:2]):
            name = (s[:60] + "...") if len(s) > 60 else s
            tasks.append({"name": f"Auto-task {i+1}: {name}", "description": s})

    # Call the side-effect helpers (they will print/stub as appropriate).
    try:
        save_tasks_to_trello(tasks)
    except Exception as e:
        print(f"[Error] save_tasks_to_trello failed: {e}")

    try:
        send_message_to_channel(f"{len(tasks)} New tasks have been added to Trello!")
    except Exception as e:
        print(f"[Error] send_message_to_channel failed: {e}")

    # Return messages list containing the JSON-serialized tasks as content.
    return {"messages": [SystemMessage(content=json.dumps(tasks))]}


# Build the graph
graph = StateGraph(State)

graph.add_node("run_team", run_team)
graph.add_node("tools", tool_node)

graph.add_edge(START, "run_team")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")]})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
