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
    """Subgraph node: plan_trip

    This node simulates the TravelPlanningCrew by producing a deterministic,
    integrated travel plan from the incoming request. It appends a sequence of
    agent-like contributions to the state's messages and sets the final plan.
    """
    # Start from any incoming messages
    messages = list(state.get("messages", []) or [])

    request = state.get("request", "Plan a 10 day trip to Luxembourg.")

    # Deterministic, self-contained "agent" outputs (no external LLM calls),
    # to ensure the generated program runs in environments without API access.
    planner_output = (
        f"Planner: High-level itinerary for the request '{request}':\n"
        "- Overview: 10-day trip with a mix of city sightseeing and nature.\n"
        "- Accommodation: Central hotel in the main city with easy transit access.\n"
        "- Transport: Fly into main airport, use local train/bus for intercity legs.\n"
        "- Day-by-day (high-level):\n"
        "  Day 1: Arrival, settle in, light city walk.\n"
        "  Days 2-3: Main city sightseeing and museums.\n"
        "  Days 4-6: Day trips to nearby towns and nature areas.\n"
        "  Days 7-9: Explore local neighborhoods, markets, and food.\n"
        "  Day 10: Pack and depart.\n"
    )
    messages.append(HumanMessage(content=planner_output))

    local_output = (
        "Local Guide: Authentic activities and places to integrate into the itinerary:\n"
        "- Visit the local farmers' market on Day 2 for breakfast and local crafts.\n"
        "- Take a guided walking tour focused on historic neighborhoods on Day 3.\n"
        "- Reserve a half-day with a local guide for a less-touristy town on Day 5.\n"
        "- Try the recommended regional dish at a family-run restaurant on Day 8.\n"
    )
    messages.append(HumanMessage(content=local_output))

    language_output = (
        "Language Adviser: Communication tips and language notes:\n"
        "- Learn key phrases: hello, please, thank you, excuse me, do you speak English?.\n"
        "- Carry a short printed address of your accommodation in the local language.\n"
        "- Be aware of polite forms (e.g., formal vs informal) when addressing shopkeepers.\n    "
    )
    messages.append(HumanMessage(content=language_output))

    summary_output = (
        "Travel Summary Writer: Final integrated travel plan (TERMINATE):\n\n"
        f"{planner_output}\n"
        f"{local_output}\n"
        f"{language_output}\n"
        "End of plan. TERMINATE"
    )
    messages.append(HumanMessage(content=summary_output))

    # Set the final plan text in the state for publishing
    return {"messages": messages, "plan": summary_output}


def publish(state: TravelPlanningState) -> dict:
    """Node: publish

    Publish simply returns the accumulated messages and the final plan.
    """
    messages = state.get("messages", [])
    plan = state.get("plan", "")
    # Return both so the flow can inspect & print them
    return {"messages": messages, "plan": plan}


# Build the graph
graph = StateGraph(TravelPlanningState)

graph.add_node("plan_trip", plan_trip)
graph.add_node("publish", publish)

graph.add_edge(START, "plan_trip")
graph.add_edge("plan_trip", "publish")
graph.add_edge("publish", END)

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
