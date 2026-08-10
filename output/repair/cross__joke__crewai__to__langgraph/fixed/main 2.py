"""
Auto-generated LangGraph application: joke
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class JokeState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    final_joke: str
    improved_joke: str
    joke: str
    topic: str

model = ChatOpenAI(model="gpt-4o")


def generate_joke(state: JokeState) -> dict:
    """Subgraph node: generate_joke"""
    # Simple deterministic joke generator based on the topic.
    topic = state.get("topic", "cats")
    # Produce a short joke without a clear punchline to force the improve step.
    joke = f"A {topic} walked into a room and quietly took over the meeting"
    return {"joke": joke}


def check_punchline(state: JokeState) -> dict:
    """Node: check_punchline"""
    # No LLM call here; router will inspect the joke text.
    # Return the joke unchanged.
    return {"joke": state.get("joke", "")}


def route_check_punchline(state: JokeState) -> str:
    """Router: check_punchline"""
    """Gate function: skip improvements if the joke already has a punchline."""
    joke_text = state.get("joke", "") or ""
    if "?" in joke_text or "!" in joke_text:
        return "Pass"
    return "Fail"


def improve_joke(state: JokeState) -> dict:
    """Subgraph node: improve_joke"""
    # Simple deterministic "improver" that adds wordplay.
    base = state.get("joke", "")
    if not base:
        base = "Something odd happened"
    improved = f"{base}. It was purr-fectly planned!"
    return {"improved_joke": improved}


def polish_joke(state: JokeState) -> dict:
    """Subgraph node: polish_joke"""
    # Polisher adds a surprising twist.
    improved = state.get("improved_joke") or state.get("joke", "")
    final = f"{improved} Then everyone realized it was all a cat-alyst for laughter!"
    return {"final_joke": final}


# Build the graph
graph = StateGraph(JokeState)

graph.add_node("generate_joke", generate_joke)
graph.add_node("check_punchline", check_punchline)
graph.add_node("improve_joke", improve_joke)
graph.add_node("polish_joke", polish_joke)

graph.add_edge(START, "generate_joke")
graph.add_edge("generate_joke", "check_punchline")
graph.add_conditional_edges(
    "check_punchline",
    route_check_punchline,
    {
        "Fail": "improve_joke",
        "Pass": END,
    },
)
graph.add_edge("improve_joke", "polish_joke")
graph.add_edge("polish_joke", END)

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke(
        {
            "messages": [HumanMessage(content="Start the task.")],
            "final_joke": "",
            "improved_joke": "",
            "joke": "",
            "topic": "cats",
        }
    )
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
