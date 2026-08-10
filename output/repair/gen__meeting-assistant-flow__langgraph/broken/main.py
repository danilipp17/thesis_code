"""
Auto-generated LangGraph application: meeting_assistant_flow
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class MeetingState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    tasks: list[dict]
    transcript: str

model = ChatOpenAI(model="gpt-4o")


def load_meeting_notes(state: MeetingState) -> dict:
    """Node: load_meeting_notes"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def analyze_meeting(state: MeetingState) -> dict:
    """Extract actionable tasks from a meeting transcript."""
    task_prompt = f"Analyze the provided meeting transcript and generate a JSON list of {{name, description}} objects.\n\nTranscript:\n{state['transcript']}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"tasks": response.content}


def upload_trello(state: MeetingState) -> dict:
    """Node: upload_trello"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def save_csv(state: MeetingState) -> dict:
    """Node: save_csv"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def notify_slack(state: MeetingState) -> dict:
    """Node: notify_slack"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(MeetingState)

graph.add_node("load_meeting_notes", load_meeting_notes)
graph.add_node("analyze_meeting", analyze_meeting)
graph.add_node("upload_trello", upload_trello)
graph.add_node("save_csv", save_csv)
graph.add_node("notify_slack", notify_slack)

graph.add_edge(START, "load_meeting_notes")
graph.add_edge("load_meeting_notes", "analyze_meeting")
graph.add_edge("analyze_meeting", "upload_trello")
graph.add_edge("upload_trello", "save_csv")

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
