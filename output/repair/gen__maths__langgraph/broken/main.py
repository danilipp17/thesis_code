"""
Auto-generated LangGraph application: maths
"""

import dotenv
from typing import Annotated, Sequence, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from tools import add, subtract, multiply
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    """Graph state."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [add, subtract, multiply]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def our_agent(state: AgentState) -> dict:
    """Node: our_agent"""
    system_prompt = SystemMessage(content='You are my AI assistant, please answer my query to the best of your ability.')
    messages = [system_prompt] + state.get("messages", [])
    response = model_with_tools.invoke(messages)
    return {"messages": response.content}


def route_our_agent(state: AgentState) -> str:
    """Router: our_agent"""
    last_message = state['messages'][-1]


# Build the graph
graph = StateGraph(AgentState)

graph.add_node("our_agent", our_agent)
graph.add_node("tools", tool_node)

graph.add_edge(START, "our_agent")
graph.add_conditional_edges(
    "our_agent",
    route_our_agent,
    {
        "continue": "tools",
        "end": END
    },
)
graph.add_edge("tools", "our_agent")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")]})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
