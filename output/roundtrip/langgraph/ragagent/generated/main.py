"""
Auto-generated LangGraph application: ragagent
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from tools import retriever_tool
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [retriever_tool]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def llm(state: State) -> dict:
    """Function to call the LLM with the current state."""
    system_prompt = SystemMessage(content='system_prompt')
    messages = [system_prompt] + state.get("messages", [])
    response = model_with_tools.invoke(messages)
    return {"messages": response.content}


def retriever_agent(state: State) -> dict:
    """Execute tool calls from the LLM's response."""
    messages = state.get("messages", [])
    response = model_with_tools.invoke(messages)
    return {"messages": response.content}


# Build the graph
graph = StateGraph(State)

graph.add_node("llm", llm)
graph.add_node("retriever_agent", retriever_agent)
graph.add_node("tools", tool_node)

graph.add_edge(START, "llm")
graph.add_edge("tools", "llm")
graph.add_edge("tools", "retriever_agent")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
