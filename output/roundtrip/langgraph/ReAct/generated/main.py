"""
Auto-generated LangGraph application: ReAct
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.messages import SystemMessage, HumanMessage

from tools import add, multiply, subtract
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [add, multiply, subtract]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def our_agent(state: State) -> dict:
    """Node: our_agent"""
    system_prompt = SystemMessage(content=
        """You are my AI assistant, please answer my query to the best of your ability."""
    )
    messages = [system_prompt] + state.get("messages", [])
    response = model_with_tools.invoke(messages)
    return {"messages": response.content}


def route_our_agent(state: State) -> str:
    """Router: our_agent"""
    messages = state['messages']
    last_message = messages[-1]
    if not last_message.tool_calls:
        return 'end'
    else:
        return 'continue'


# Build the graph
graph = StateGraph(State)

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
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
