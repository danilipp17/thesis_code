"""
Auto-generated LangGraph application: AI_News_System
"""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from tools import web_search
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""

    messages: Annotated[list, add_messages]
    write_task_output: str
    research_task_output: str


model = ChatOpenAI(model="gpt-4o")

tools = [web_search]
tool_node = ToolNode(tools)

researcher_model = model.bind_tools([web_search])


def start_research(state: State) -> dict:
    """Node: start_research"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def review_research(state: State) -> dict:
    """Node: review_research"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def write_article(state: State) -> dict:
    """Node: write_article"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(State)

graph.add_node("start_research", start_research)
graph.add_node("review_research", review_research)
graph.add_node("write_article", write_article)
graph.add_node("tools", tool_node)

graph.add_edge(START, "start_research")
graph.add_edge("start_research", "write_article")
graph.add_edge(
    "tools", "start_research"
)  # Fixed to route back to the node, not the agent

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
