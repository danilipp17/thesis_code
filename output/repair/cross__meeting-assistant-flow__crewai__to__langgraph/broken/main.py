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


class MeetingState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    tasks: List[MeetingTask]
    transcript: str

model = ChatOpenAI(model="gpt-4")


def load_meeting_notes(state: MeetingState) -> dict:
    """Subgraph node: load_meeting_notes"""
    # TODO: Initialize and invoke the MeetingAssistantCrew compiled subgraph here
    return {"messages": []}


def generate_tasks_from_meeting_transcript(state: MeetingState) -> dict:
    """Subgraph node: generate_tasks_from_meeting_transcript"""
    # TODO: Initialize and invoke the MeetingAssistantCrew compiled subgraph here
    return {"messages": []}


def add_tasks_to_trello(state: MeetingState) -> dict:
    """Node: add_tasks_to_trello"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def save_new_tasks_to_csv(state: MeetingState) -> dict:
    """Node: save_new_tasks_to_csv"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def send_slack_notification(state: MeetingState) -> dict:
    """Node: send_slack_notification"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(MeetingState)

graph.add_node("load_meeting_notes", load_meeting_notes)
graph.add_node("generate_tasks_from_meeting_transcript", generate_tasks_from_meeting_transcript)
graph.add_node("add_tasks_to_trello", add_tasks_to_trello)
graph.add_node("save_new_tasks_to_csv", save_new_tasks_to_csv)
graph.add_node("send_slack_notification", send_slack_notification)

graph.add_edge(START, "load_meeting_notes")
graph.add_edge("load_meeting_notes", "generate_tasks_from_meeting_transcript")

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
