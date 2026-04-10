"""
research_assistant.py
=====================
A simple LangGraph research assistant with two agents:
- A Researcher agent that gathers information
- A Writer agent that produces a summary

This example demonstrates:
- StateGraph definition with TypedDict state
- Multiple tool-calling agents as nodes
- Conditional routing via a router function
- Tool definition with @tool decorator

This serves as a test fixture for the OSCIN LangGraph parser.
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class ResearchState(TypedDict):
    messages: Annotated[list, add_messages]
    research_notes: str
    final_summary: str


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def search_web(query: str) -> str:
    """Search the web for information on a given topic."""
    return f"Search results for: {query}"


@tool
def save_notes(notes: str) -> str:
    """Save research notes for later use."""
    return f"Notes saved: {notes}"


# ---------------------------------------------------------------------------
# Agents (LLM nodes)
# ---------------------------------------------------------------------------

llm = ChatOpenAI(model="gpt-4o", temperature=0)

researcher_llm = llm.bind_tools([search_web, save_notes])
writer_llm = llm


def researcher_agent(state: ResearchState) -> dict:
    """Research agent that gathers information using tools."""
    system_message = (
        "You are a research assistant. Your goal is to gather "
        "comprehensive information on the given topic. Use the "
        "search_web tool to find information and save_notes to "
        "record your findings."
    )
    messages = [{"role": "system", "content": system_message}] + state["messages"]
    response = researcher_llm.invoke(messages)
    return {"messages": [response]}


def writer_agent(state: ResearchState) -> dict:
    """Writer agent that produces a summary from research notes."""
    system_message = (
        "You are a professional writer. Your goal is to produce "
        "a clear, concise summary based on the research provided. "
        "Write in a formal academic style."
    )
    messages = [{"role": "system", "content": system_message}] + state["messages"]
    response = writer_llm.invoke(messages)
    return {"messages": [response], "final_summary": response.content}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def should_continue(state: ResearchState) -> Literal["writer", "researcher"]:
    """Route to writer if research is complete, else back to researcher."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "researcher"
    return "writer"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

workflow = StateGraph(ResearchState)

# Add nodes
workflow.add_node("researcher", researcher_agent)
workflow.add_node("writer", writer_agent)

# Add edges
workflow.add_edge(START, "researcher")
workflow.add_conditional_edges("researcher", should_continue)
workflow.add_edge("writer", END)

# Compile
graph = workflow.compile()
