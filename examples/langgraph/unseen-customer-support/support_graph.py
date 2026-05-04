"""
Unseen example: A customer support routing graph using LangGraph.
This example was NOT used during development of the OSCIN parsers.
It tests: multiple agent nodes, branching conditional edges,
parallel-ish topology, tool usage, and state with multiple fields.
"""

import operator
from typing import Annotated, TypedDict, Sequence

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


# --- State ---

class SupportState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ticket_category: str
    priority: str
    resolved: bool


# --- Tools ---

@tool
def lookup_order(order_id: str) -> str:
    """Look up order details by order ID."""
    return f"Order {order_id}: shipped, arriving in 2 days"


@tool
def check_account_status(email: str) -> str:
    """Check customer account status by email."""
    return f"Account {email}: active, premium tier"


@tool
def create_ticket(description: str, priority: str) -> str:
    """Create a support ticket with given description and priority."""
    return f"Ticket created: {description} (priority: {priority})"


# --- Models ---

classifier_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent_llm = ChatOpenAI(model="gpt-4o")

tools = [lookup_order, check_account_status, create_ticket]
tool_node = ToolNode(tools)

agent_with_tools = agent_llm.bind_tools(tools)


# --- Agent nodes ---

def classifier(state: SupportState) -> dict:
    """Classify the customer inquiry into a category."""
    system = SystemMessage(
        content="You are a support ticket classifier. Categorize the customer message as 'billing', 'technical', or 'general'."
    )
    messages = [system] + state["messages"]
    response = classifier_llm.invoke(messages)
    category = response.content.strip().lower()
    if "billing" in category:
        return {"ticket_category": "billing", "messages": [response]}
    elif "technical" in category:
        return {"ticket_category": "technical", "messages": [response]}
    else:
        return {"ticket_category": "general", "messages": [response]}


def billing_agent(state: SupportState) -> dict:
    """Handle billing-related inquiries."""
    system = SystemMessage(
        content="You are a billing support specialist. Help customers with payment issues, refunds, and account billing questions. Use tools to look up orders and accounts."
    )
    messages = [system] + state["messages"]
    response = agent_with_tools.invoke(messages)
    return {"messages": [response]}


def technical_agent(state: SupportState) -> dict:
    """Handle technical support inquiries."""
    system = SystemMessage(
        content="You are a technical support engineer. Help customers troubleshoot product issues and bugs. Create tickets for unresolved issues."
    )
    messages = [system] + state["messages"]
    response = agent_with_tools.invoke(messages)
    return {"messages": [response]}


def general_agent(state: SupportState) -> dict:
    """Handle general inquiries and FAQ."""
    system = SystemMessage(
        content="You are a general support agent. Answer common questions about products, policies, and services."
    )
    messages = [system] + state["messages"]
    response = agent_llm.invoke(messages)
    return {"messages": [response], "resolved": True}


def escalation_checker(state: SupportState) -> dict:
    """Check if the issue needs escalation."""
    system = SystemMessage(
        content="Review the conversation and determine if the issue is resolved or needs human escalation."
    )
    messages = [system] + state["messages"]
    response = agent_llm.invoke(messages)
    return {"messages": [response]}


# --- Routing ---

def route_by_category(state: SupportState) -> str:
    """Route to the appropriate specialist based on ticket category."""
    category = state.get("ticket_category", "general")
    if category == "billing":
        return "billing"
    elif category == "technical":
        return "technical"
    else:
        return "general"


def should_use_tools(state: SupportState) -> str:
    """Check if the last message has tool calls."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "check_escalation"


# --- Build Graph ---

graph = StateGraph(SupportState)

# Add nodes
graph.add_node("classifier", classifier)
graph.add_node("billing_agent", billing_agent)
graph.add_node("technical_agent", technical_agent)
graph.add_node("general_agent", general_agent)
graph.add_node("tools", tool_node)
graph.add_node("escalation_checker", escalation_checker)

# Entry
graph.add_edge(START, "classifier")

# Route from classifier to specialist
graph.add_conditional_edges(
    "classifier",
    route_by_category,
    {
        "billing": "billing_agent",
        "technical": "technical_agent",
        "general": "general_agent",
    },
)

# Billing and technical agents may call tools
graph.add_conditional_edges(
    "billing_agent",
    should_use_tools,
    {"tools": "tools", "check_escalation": "escalation_checker"},
)
graph.add_conditional_edges(
    "technical_agent",
    should_use_tools,
    {"tools": "tools", "check_escalation": "escalation_checker"},
)

# Tools return to the agent that called them
graph.add_edge("tools", "billing_agent")

# General agent goes straight to end
graph.add_edge("general_agent", END)

# Escalation checker ends
graph.add_edge("escalation_checker", END)

# Compile
app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({
        "messages": [HumanMessage(content="I was charged twice for my last order #12345")],
        "ticket_category": "",
        "priority": "medium",
        "resolved": False,
    })
    print(result["messages"][-1].content)
