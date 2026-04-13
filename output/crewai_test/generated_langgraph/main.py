"""
Auto-generated LangGraph application: AcademicFlow
"""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from tools import academic_search_tool
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    write_paper_task_output: str
    gather_literature_task_output: str

model = ChatOpenAI(model="gpt-4o")

tools = [academic_search_tool]
tool_node = ToolNode(tools)

senior_researcher_model = model.bind_tools([academic_search_tool])


def initialize_research(state: State) -> dict:
    """Node: initialize_research"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def conduct_research(state: State) -> dict:
    """Node: conduct_research"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def review_outcome(state: State) -> dict:
    """Node: review_outcome"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def route_review_outcome(state: State) -> str:
    """Router: review_outcome"""
    if self.state.status == "SUCCESS":
        return "publish_paper"
    elif self.state.status == "FAILED":
        return "abort_research"


def publish_paper(state: State) -> dict:
    """Node: publish_paper"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def abort_research(state: State) -> dict:
    """Node: abort_research"""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(State)

graph.add_node("initialize_research", initialize_research)
graph.add_node("conduct_research", conduct_research)
graph.add_node("review_outcome", review_outcome)
graph.add_node("publish_paper", publish_paper)
graph.add_node("abort_research", abort_research)
graph.add_node("tools", tool_node)

graph.add_edge(START, "initialize_research")
graph.add_edge("initialize_research", "conduct_research")
graph.add_conditional_edges(
    "review_outcome",
    route_review_outcome,
    {
        "abort_research": "abort_research",
        "publish_paper": "publish_paper"
    },
)
graph.add_edge("review_outcome", "publish_paper")
graph.add_edge("review_outcome", "abort_research")
graph.add_edge("tools", "senior_researcher")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
