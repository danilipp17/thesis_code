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
    messages = state.get("messages", []) or []

    sys = SystemMessage(
        content=(
            "Joke Generator — role: A witty comedian who comes up with sharp, short jokes. "
            "Goal: Write a short joke on the given topic."
        )
    )
    topic = state.get("topic", "cats")
    human = HumanMessage(content=f"Write a short joke about {topic}.")

    # call the LLM
    response = model.invoke([sys, human])

    # store the response as the generated joke and append to messages
    joke_text = getattr(response, "content", str(response))
    new_messages = messages + [sys, human, response]

    return {"messages": new_messages, "joke": joke_text}


def check_punchline(state: JokeState) -> dict:
    """Node: check_punchline"""
    # This node just passes state along; the routing function will inspect state["joke"].
    return {"messages": state.get("messages", []) or []}


def route_check_punchline(state: JokeState) -> str:
    """Router: check_punchline"""
    """Gate function: skip improvements if the joke already has a punchline."""
    joke = state.get("joke", "") or ""
    if "?" in joke or "!" in joke:
        return "Pass"
    return "Fail"


def improve_joke(state: JokeState) -> dict:
    """Subgraph node: improve_joke"""
    messages = state.get("messages", []) or []

    sys = SystemMessage(
        content=(
            "Joke Improver — role: A seasoned writer who polishes jokes for punch. "
            "Goal: Improve a joke by adding clever wordplay."
        )
    )
    joke_in = state.get("joke", "")
    human = HumanMessage(content=f"Make this joke funnier by adding wordplay: {joke_in}")

    response = model.invoke([sys, human])

    improved = getattr(response, "content", str(response))
    new_messages = messages + [sys, human, response]

    return {"messages": new_messages, "improved_joke": improved}


def polish_joke(state: JokeState) -> dict:
    """Subgraph node: polish_joke"""
    messages = state.get("messages", []) or []

    sys = SystemMessage(
        content=(
            "Joke Polisher — role: A storyteller who knows how to twist endings for effect. "
            "Goal: Add a surprising twist to a joke."
        )
    )
    improved = state.get("improved_joke", "") or state.get("joke", "")
    human = HumanMessage(content=f"Add a surprising twist to this joke: {improved}")

    response = model.invoke([sys, human])

    final = getattr(response, "content", str(response))
    new_messages = messages + [sys, human, response]

    return {"messages": new_messages, "final_joke": final}


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
        "Fail": "improve_joke"
    },
)
graph.add_edge("improve_joke", "polish_joke")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "final_joke": "", "improved_joke": "", "joke": "", "topic": "cats"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
