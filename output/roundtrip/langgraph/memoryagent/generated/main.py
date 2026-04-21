"""
Auto-generated LangGraph application: memoryagent
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI


class State(TypedDict):
    """Graph state."""
    messages: List[Union[HumanMessage, AIMessage]]

model = ChatOpenAI(model="gpt-4o")


def process(state: State) -> dict:
    """This node will solve the request you input"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(State)

graph.add_node("process", process)

graph.add_edge(START, "process")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
