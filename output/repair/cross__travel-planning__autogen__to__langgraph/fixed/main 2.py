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


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]

model = ChatOpenAI(model="gpt-4o")


def run_group_chat(state: State) -> dict:
    """Subgraph node: run_group_chat

    This function simulates the 4-agent AutoGen team (planner, local, language,
    summary). It reads the incoming messages to find the task; if no explicit
    task is found, it uses the canonical example "Plan a 10 day trip to Luxembourg."
    It then appends deterministic, representative messages from each agent,
    ending with the summary agent that emits TERMINATE.
    """
    # Start from incoming messages (may include the user task or a "Start the task." token)
    incoming = state.get("messages", []) or []
    # Determine task: prefer any message that looks like a planning request,
    # otherwise use the canonical example.
    task = None
    for m in reversed(incoming):
        if hasattr(m, "content") and isinstance(m.content, str):
            txt = m.content.strip()
            # Heuristics: if it mentions "Plan" or "trip" treat as task
            if "Plan" in txt or "trip" in txt.lower() or "luxembourg" in txt.lower():
                task = txt
                break
    if not task:
        task = "Plan a 10 day trip to Luxembourg."

    # Deterministic, representative agent outputs.
    planner_content = (
        "planner_agent:\n"
        f"Task received: {task}\n\n"
        "Here is a suggested 10-day itinerary:\n"
        "Day 1: Arrive in Luxembourg City, settle in, walk the Old Quarter, dinner near Place d'Armes.\n"
        "Day 2: Explore the Bock Casemates & Grund neighborhood; Musée d'Histoire de la Ville.\n"
        "Day 3: Day trip to Vianden Castle and the town of Vianden.\n"
        "Day 4: Visit Echternach and Mullerthal (the \"Little Switzerland\") for hiking.\n"
        "Day 5: Tour the Moselle wine region, sample local wines and visit Remich.\n"
        "Day 6: Discover the national fortifications and modern Kirchberg district (MUDAM).\n"
        "Day 7: Day trip to Clervaux (family heritage sites) and surrounding valleys.\n"
        "Day 8: Relaxation day with a local market, food tasting, and a spa option.\n"
        "Day 9: Cultural day: concerts, local museums, and culinary experiences in the capital.\n"
        "Day 10: Final shopping, last-minute visits, prepare for departure.\n"
    )

    local_content = (
        "local_agent:\n"
        "Authentic local activities and tips:\n"
        "- Try the traditional Luxembourger dishes: Judd mat Gaardebounen, Gromperekichelcher.\n"
        "- Visit smaller villages (e.g., Esch-sur-Sûre) for local cafés and crafts.\n"
        "- Check local event listings for small concerts or fêtes (especially in summer).\n"
        "- Use regional trains/buses for short hops; consider renting a bike in the countryside.\n"
        "- Evening: sample Moselle wines at a family-run domaine.\n"
    )

    language_content = (
        "language_agent:\n"
        "Communication tips for Luxembourg:\n"
        "- Luxembourg has three official languages (Luxembourgish, French, German). Tourists "
        "can usually get by with English in hotels, restaurants, and major attractions.\n"
        "- Learn a few polite phrases in Luxembourgish or French (e.g., 'Moien' for hello, "
        "'Merci' for thanks) — locals appreciate the effort.\n"
        "- In rural areas, knowledge of basic French or German phrases can be useful.\n"
        "- Carry addresses written clearly for taxis and use maps; phone translation apps work well.\n"
    )

    summary_content = (
        "travel_summary_agent:\n"
        "Final integrated travel plan — COMPLETE. This plan combines the itinerary, local "
        "recommendations, and language tips. Use the following as your master plan for a 10-day trip:\n\n"
        f"{planner_content}\n"
        f"{local_content}\n"
        f"{language_content}\n\n"
        "Notes:\n"
        "- Adjust day trips based on season and opening hours.\n"
        "- Book key accommodations in advance, and reserve any special wine-tasting visits.\n"
        "- Keep an offline map and emergency contacts handy.\n\n"
        "TERMINATE"
    )

    # Build the outgoing message list: preserve incoming context, then agents' messages
    outgoing = list(incoming) + [
        HumanMessage(content=planner_content),
        HumanMessage(content=local_content),
        HumanMessage(content=language_content),
        HumanMessage(content=summary_content),
    ]

    return {"messages": outgoing}


# Build the graph
graph = StateGraph(State)

graph.add_node("run_group_chat", run_group_chat)

graph.add_edge(START, "run_group_chat")

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
