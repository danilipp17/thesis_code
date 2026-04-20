"""
Auto-generated LangGraph application: research_assistant
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.messages import SystemMessage, HumanMessage

from tools import save_notes, search_web
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    research_notes: str
    final_summary: str

model = ChatOpenAI(model="gpt-4o")

tools = [save_notes, search_web]
tool_node = ToolNode(tools)

researcher_model = model.bind_tools([save_notes, search_web])


def researcher(state: State) -> dict:
    """Node: researcher"""
    system_prompt = SystemMessage(content=
        """You are a research assistant. Your goal is to gather comprehensive information on the given topic. Use the search_web tool to find information and save_notes to record your findings."""
    )
    messages = [system_prompt] + state.get("messages", [])
    response = researcher_model.invoke(messages)
    return {"messages": response.content}


def route_researcher(state: State) -> str:
    """Router: researcher"""
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return 'researcher'
    return 'writer'


def writer(state: State) -> dict:
    """Node: writer"""
    system_prompt = SystemMessage(content=
        """You are a professional writer. Your goal is to produce a clear, concise summary based on the research provided. Write in a formal academic style."""
    )
    messages = [system_prompt] + state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": response.content, "final_summary": response.content}


# Build the graph
graph = StateGraph(State)

graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_node("tools", tool_node)

graph.add_edge(START, "researcher")
graph.add_conditional_edges(
    "researcher",
    route_researcher,
    {
        "researcher": "researcher",
        "writer": "writer"
    },
)
graph.add_edge("researcher", "writer")
graph.add_edge("tools", "researcher")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
