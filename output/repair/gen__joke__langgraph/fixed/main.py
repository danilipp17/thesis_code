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


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    final_joke: str
    improved_joke: str
    joke: str
    topic: str

model = ChatOpenAI(model="gpt-4o")


def generate_joke(state: State) -> dict:
    """First LLM call to generate initial joke"""
    topic = state.get("topic", "a random topic")
    prompt = f"Write a short, punchy joke about {topic}"
    response = model.invoke(prompt)
    return {"joke": response.content}


def route_generate_joke(state: State) -> str:
    """Router: generate_joke"""
    if '?' in state.get('joke', '') or '!' in state.get('joke', ''):
        return 'Pass'
    return 'Fail'


def improve_joke(state: State) -> dict:
    """Second LLM call to improve the joke"""
    joke = state.get("joke", "")
    prompt = f"Make this joke funnier by adding wordplay and keeping it short:\n\n{joke}"
    response = model.invoke(prompt)
    return {"improved_joke": response.content}


def polish_joke(state: State) -> dict:
    """Third LLM call for final polish"""
    improved = state.get("improved_joke", state.get("joke", ""))
    prompt = f"Add a surprising twist to this joke and polish wording:\n\n{improved}"
    response = model.invoke(prompt)
    return {"final_joke": response.content}


# Build the graph
graph = StateGraph(State)

graph.add_node("generate_joke", generate_joke)
graph.add_node("improve_joke", improve_joke)
graph.add_node("polish_joke", polish_joke)

graph.add_edge(START, "generate_joke")
graph.add_conditional_edges(
    "generate_joke",
    route_generate_joke,
    {
        "Fail": "improve_joke",
        "Pass": END
    },
)

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    # Provide a representative concrete input
    result = app.invoke({"topic": "cats"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
