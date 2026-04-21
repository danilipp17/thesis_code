"""
Auto-generated LangGraph application: drafter
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from tools import save, update
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [save, update]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def agent(state: State) -> dict:
    """Node: agent"""
    system_prompt = SystemMessage(content='f"\\n    You are Drafter, a helpful writing assistant. You are going to help the user update and modify documents.\\n    \\n    - If the user wants to update or modify content, use the \'update\' tool with the complete updated content.\\n    - If the user wants to save and finish, you need to use the \'save\' tool.\\n    - Make sure to always show the current document state after modifications.\\n    \\n    The current document content is:{document_content}\\n    "')
    messages = [system_prompt] + state.get("messages", [])
    response = model_with_tools.invoke(messages)
    return {"messages": response.content}


# Build the graph
graph = StateGraph(State)

graph.add_node("agent", agent)
graph.add_node("tools", tool_node)

graph.add_edge(START, "agent")
graph.add_edge("tools", "agent")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
