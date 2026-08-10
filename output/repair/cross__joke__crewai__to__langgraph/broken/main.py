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
    # TODO: Initialize and invoke the GenerateJokeCrew compiled subgraph here
    return {"messages": []}


def check_punchline(state: JokeState) -> dict:
    """Node: check_punchline"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def route_check_punchline(state: JokeState) -> str:
    """Router: check_punchline"""
    """Gate function: skip improvements if the joke already has a punchline."""
    if "?" in self.state.joke or "!" in self.state.joke:
        return "Pass"
    return "Fail"


def improve_joke(state: JokeState) -> dict:
    """Subgraph node: improve_joke"""
    # TODO: Initialize and invoke the ImproveJokeCrew compiled subgraph here
    return {"messages": []}


def polish_joke(state: JokeState) -> dict:
    """Subgraph node: polish_joke"""
    # TODO: Initialize and invoke the PolishJokeCrew compiled subgraph here
    return {"messages": []}


# Build the graph
graph = StateGraph(JokeState)

graph.add_node("generate_joke", generate_joke)
graph.add_node("check_punchline", check_punchline)
graph.add_node("improve_joke", improve_joke)
graph.add_node("polish_joke", polish_joke)

graph.add_edge(START, "generate_joke")
graph.add_conditional_edges(
    "generate_joke",
    route_check_punchline,
    {
        "improve_joke": "improve_joke"
    },
)
graph.add_edge("Fail", "improve_joke")
graph.add_edge("check_punchline", "improve_joke")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "final_joke": "sample final_joke", "improved_joke": "sample improved_joke", "joke": "sample joke", "topic": "sample topic"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
