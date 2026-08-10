"""
Auto-generated LangGraph application: tech_blog
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class TechBlogState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    final_post: str
    topic: str

model = ChatOpenAI(model="gpt-4o")


def write_blog(state: TechBlogState) -> dict:
    """Subgraph node: write_blog"""
    # TODO: Initialize and invoke the TechBlogCrew compiled subgraph here
    return {"messages": []}


def publish(state: TechBlogState) -> dict:
    """Node: publish"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(TechBlogState)

graph.add_node("write_blog", write_blog)
graph.add_node("publish", publish)

graph.add_edge(START, "write_blog")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "final_post": "sample final_post", "topic": "sample topic"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
