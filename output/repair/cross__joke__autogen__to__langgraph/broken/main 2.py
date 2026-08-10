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

model = ChatOpenAI(model="gpt-4o")


def run_team(state: State) -> dict:
    """Subgraph node: run_team"""
    # TODO: Initialize and invoke the SubGraph compiled subgraph here
    return {"messages": []}


# Build the graph
graph = StateGraph(State)

graph.add_node("run_team", run_team)

graph.add_edge(START, "run_team")

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
