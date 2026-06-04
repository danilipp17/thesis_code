"""
travel-planning — LangGraph port of the AutoGen original.

Original: examples/parallel/travel-planning/autogen — four AssistantAgents
(planner, local, language, summary) in a SelectorGroupChat with
TextMentionTermination("TERMINATE").

LangGraph mapping:
  - AssistantAgent             -> LangGraph node (LLM call)
  - SelectorGroupChat dynamic  -> sequential StateGraph
    routing                       (LangGraph has no direct selector
                                   primitive; documented as a thesis
                                   finding)
  - shared transcript state    -> TypedDict ``TravelState`` with a
                                   ``plan`` accumulator updated by each
                                   node.
"""

from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatOpenAI(model="gpt-4o")


class TravelState(TypedDict):
    request: str
    plan: str
    local_notes: str
    language_notes: str
    final_plan: str


def planner_agent(state: TravelState) -> TravelState:
    """Sketch the initial itinerary."""
    msg = llm.invoke(
        "You are a helpful assistant that can suggest a travel plan for a "
        f"user based on their request.\n\nRequest: {state['request']}"
    )
    return {"plan": msg.content}


def local_agent(state: TravelState) -> TravelState:
    """Add local activities."""
    msg = llm.invoke(
        "You are a helpful assistant that can suggest authentic and "
        "interesting local activities or places to visit. Given the "
        "initial plan, contribute concrete local suggestions.\n\n"
        f"Plan so far:\n{state['plan']}"
    )
    return {"local_notes": msg.content}


def language_agent(state: TravelState) -> TravelState:
    """Add language/communication tips."""
    msg = llm.invoke(
        "You review travel plans and provide feedback on important tips "
        "about how best to address language or communication challenges "
        "for the destination.\n\n"
        f"Plan so far:\n{state['plan']}\n\n"
        f"Local suggestions:\n{state['local_notes']}"
    )
    return {"language_notes": msg.content}


def travel_summary_agent(state: TravelState) -> TravelState:
    """Integrate everything into the final plan."""
    msg = llm.invoke(
        "You compile all suggestions and advice from the other agents "
        "and provide a detailed final travel plan. Your final response "
        "must be the complete plan. When the plan is complete, conclude "
        "with TERMINATE.\n\n"
        f"Initial plan:\n{state['plan']}\n\n"
        f"Local notes:\n{state['local_notes']}\n\n"
        f"Language notes:\n{state['language_notes']}"
    )
    return {"final_plan": msg.content}


workflow = StateGraph(TravelState)
workflow.add_node("planner_agent", planner_agent)
workflow.add_node("local_agent", local_agent)
workflow.add_node("language_agent", language_agent)
workflow.add_node("travel_summary_agent", travel_summary_agent)

workflow.add_edge(START, "planner_agent")
workflow.add_edge("planner_agent", "local_agent")
workflow.add_edge("local_agent", "language_agent")
workflow.add_edge("language_agent", "travel_summary_agent")
workflow.add_edge("travel_summary_agent", END)

app = workflow.compile()


if __name__ == "__main__":
    result = app.invoke(
        {
            "request": "Plan a 10 day trip to Luxembourg.",
            "plan": "",
            "local_notes": "",
            "language_notes": "",
            "final_plan": "",
        }
    )
    print(result["final_plan"])
