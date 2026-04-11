"""
Auto-generated LangGraph application: SelfEvaluationLoopSystem
"""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

from tools import character_counter_tool
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [character_counter_tool]
model_with_tools = model.bind_tools(tools)
tool_node = ToolNode(tools)


def generate_shakespeare_x_post(state: State) -> State:
    """Node: generate_shakespeare_x_post"""
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def evaluate_x_post(state: State) -> str:
    """Router: evaluate_x_post"""
    # if condition:
    #     return "generate_shakespeare_x_post"
    # return "max_retry_exceeded_exit"
    # return "save_result"
    return "generate_shakespeare_x_post"  # TODO: implement routing logic


def save_result(state: State) -> State:
    """Node: save_result"""
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def max_retry_exceeded_exit(state: State) -> State:
    """Node: max_retry_exceeded_exit"""
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(State)

graph.add_node("generate_shakespeare_x_post", generate_shakespeare_x_post)
graph.add_node("save_result", save_result)
graph.add_node("max_retry_exceeded_exit", max_retry_exceeded_exit)
graph.add_node("tools", tool_node)

graph.add_edge(START, "generate_shakespeare_x_post")
graph.add_conditional_edges(
    "evaluate_x_post",
    evaluate_x_post,
    {
        "generate_shakespeare_x_post": "generate_shakespeare_x_post",
        "max_retry_exceeded_exit": "max_retry_exceeded_exit",
        "save_result": "save_result"
    },
)
graph.add_edge("save_result", END)
graph.add_edge("max_retry_exceeded_exit", END)

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
