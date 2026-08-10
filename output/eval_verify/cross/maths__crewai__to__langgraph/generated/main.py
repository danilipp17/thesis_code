"""
Auto-generated LangGraph application: maths
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools import add, subtract, multiply
from langgraph.prebuilt import ToolNode


class MathsState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    answer: str
    query: str

model = ChatOpenAI(model="gpt-4o")

tools = [add, subtract, multiply]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def reason_and_act(state: MathsState) -> dict:
    """Subgraph node: reason_and_act"""
    # TODO: Initialize and invoke the MathsCrew compiled subgraph here
    return {"messages": []}


def publish(state: MathsState) -> dict:
    """Node: publish"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(MathsState)

graph.add_node("reason_and_act", reason_and_act)
graph.add_node("publish", publish)
graph.add_node("tools", tool_node)

graph.add_edge(START, "reason_and_act")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "answer": "sample answer", "query": "sample query"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
