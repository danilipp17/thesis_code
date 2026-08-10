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


class TravelState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    final_plan: str
    language_notes: str
    local_notes: str
    plan: str
    request: str

model = ChatOpenAI(model="gpt-4o")


def planner_agent(state: TravelState) -> dict:
    """Sketch the initial itinerary."""
    task_prompt = f"Suggest a travel plan for the request: {state['request']}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"plan": response.content}


def local_agent(state: TravelState) -> dict:
    """Add local activities."""
    task_prompt = f"Given the initial plan, contribute concrete local suggestions.\n\nPlan so far:\n{state['plan']}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"local_notes": response.content}


def language_agent(state: TravelState) -> dict:
    """Add language/communication tips."""
    task_prompt = f"Plan so far:\n{state['plan']}\n\nLocal suggestions:\n{state['local_notes']}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"language_notes": response.content}


def travel_summary_agent(state: TravelState) -> dict:
    """Integrate everything into the final plan."""
    task_prompt = f"Initial plan:\n{state['plan']}\n\nLocal notes:\n{state['local_notes']}\n\nLanguage notes:\n{state['language_notes']}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"final_plan": response.content}


# Build the graph
graph = StateGraph(TravelState)

graph.add_node("planner_agent", planner_agent)
graph.add_node("local_agent", local_agent)
graph.add_node("language_agent", language_agent)
graph.add_node("travel_summary_agent", travel_summary_agent)

graph.add_edge(START, "planner_agent")
graph.add_edge("planner_agent", "local_agent")
graph.add_edge("local_agent", "language_agent")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "final_plan": "sample final_plan", "language_notes": "sample language_notes", "local_notes": "sample local_notes", "plan": "sample plan", "request": "sample request"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
