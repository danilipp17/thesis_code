"""
Auto-generated LangGraph application: email_flow
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.messages import SystemMessage, HumanMessage

from tools import serper_dev_tool, create_draft, gmail_get_thread, tavily_search_results
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    emails: List[Email]
    checked_emails_ids: set[str]

model = ChatOpenAI(model="gpt-4o")

tools = [serper_dev_tool, create_draft, gmail_get_thread, tavily_search_results]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def fetch_new_emails(state: State) -> dict:
    """Node: fetch_new_emails"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def generate_draft_responses(state: State) -> dict:
    """Node: generate_draft_responses"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(State)

graph.add_node("fetch_new_emails", fetch_new_emails)
graph.add_node("generate_draft_responses", generate_draft_responses)
graph.add_node("tools", tool_node)

graph.add_edge(START, "fetch_new_emails")
graph.add_edge("fetch_new_emails", "generate_draft_responses")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
