"""
Auto-generated LangGraph application: code_review
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools import code_analyzer
from langgraph.prebuilt import ToolNode


class CodeReviewState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    code: str
    report: str

model = ChatOpenAI(model="gpt-4o")

tools = [code_analyzer]
tool_node = ToolNode(tools)

code_reviewer_model = model.bind_tools([code_analyzer])
security_auditor_model = model.bind_tools([code_analyzer])


def review(state: CodeReviewState) -> dict:
    """Subgraph node: review"""
    # TODO: Initialize and invoke the CodeReviewCrew compiled subgraph here
    return {"messages": []}


def publish(state: CodeReviewState) -> dict:
    """Node: publish"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(CodeReviewState)

graph.add_node("review", review)
graph.add_node("publish", publish)
graph.add_node("tools", tool_node)

graph.add_edge(START, "review")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "code": "sample code", "report": "sample report"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
