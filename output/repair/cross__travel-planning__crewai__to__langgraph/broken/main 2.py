"""
Auto-generated LangGraph application: travel_planning
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class TravelPlanningState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    plan: str
    request: str

model = ChatOpenAI(model="gpt-4o")


def plan_trip(state: TravelPlanningState) -> dict:
    """Subgraph node: plan_trip"""
    # TODO: Initialize and invoke the TravelPlanningCrew compiled subgraph here
    return {"messages": []}


def publish(state: TravelPlanningState) -> dict:
    """Node: publish"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(TravelPlanningState)

graph.add_node("plan_trip", plan_trip)
graph.add_node("publish", publish)

graph.add_edge(START, "plan_trip")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "plan": "sample plan", "request": "sample request"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
