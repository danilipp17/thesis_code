"""
ReAct Agent — LangGraph implementation.

A single LLM-driven agent that interleaves reasoning steps with tool calls
(here: simple arithmetic primitives) in a Reason+Act loop. A
StateGraph alternates between the agent node and a ToolNode until the
agent stops requesting tool calls, at which point the conditional edge
routes to END.

Source: LangGraph "ReAct agent" example.
"""

from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# -- Tools --
@tool
def add(a: int, b: int):
    """This is an addition function that adds 2 numbers together."""
    return a + b


@tool
def subtract(a: int, b: int):
    """Subtraction function."""
    return a - b


@tool
def multiply(a: int, b: int):
    """Multiplication function."""
    return a * b


tools = [add, subtract, multiply]

# -- LLM --
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)


# -- Nodes --
def model_call(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(
        content="You are my AI assistant, please answer my query to the best of your ability."
    )
    response = model.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return "end"
    return "continue"


# -- Graph --
graph = StateGraph(AgentState)
graph.add_node("our_agent", model_call)
graph.add_node("tools", ToolNode(tools=tools))

graph.set_entry_point("our_agent")
graph.add_conditional_edges(
    "our_agent",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    },
)
graph.add_edge("tools", "our_agent")

app = graph.compile()


def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()


if __name__ == "__main__":
    inputs = {
        "messages": [
            ("user", "Add 40 + 12 and then multiply the result by 6.")
        ]
    }
    print_stream(app.stream(inputs, stream_mode="values"))
