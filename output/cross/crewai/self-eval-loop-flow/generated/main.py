"""
Auto-generated LangGraph application: self_eval_loop_flow
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.messages import SystemMessage, HumanMessage

from tools import character_counter_tool
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    id: str
    x_post: str
    feedback: Optional[str]
    valid: bool
    retry_count: int

model = ChatOpenAI(model="gpt-4o")

tools = [character_counter_tool]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def generate_shakespeare_x_post(state: State) -> dict:
    """Node: generate_shakespeare_x_post"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def evaluate_x_post(state: State) -> dict:
    """Node: evaluate_x_post"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def route_evaluate_x_post(state: State) -> str:
    """Router: evaluate_x_post"""
    if self.state.retry_count > 3:
        return "max_retry_exceeded"

    result = XPostReviewCrew().crew().kickoff(inputs={"x_post": self.state.x_post})
    self.state.valid = result["valid"]
    self.state.feedback = result["feedback"]

    print("valid", self.state.valid)
    print("feedback", self.state.feedback)
    self.state.retry_count += 1

    if self.state.valid:
        return "complete"

    return "retry"


def save_result(state: State) -> dict:
    """Node: save_result"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


def max_retry_exceeded_exit(state: State) -> dict:
    """Node: max_retry_exceeded_exit"""
    messages = state.get("messages", [])
    response = model.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph = StateGraph(State)

graph.add_node("generate_shakespeare_x_post", generate_shakespeare_x_post)
graph.add_node("evaluate_x_post", evaluate_x_post)
graph.add_node("save_result", save_result)
graph.add_node("max_retry_exceeded_exit", max_retry_exceeded_exit)
graph.add_node("tools", tool_node)

graph.add_edge(START, "generate_shakespeare_x_post")
graph.add_conditional_edges(
    "evaluate_x_post",
    route_evaluate_x_post,
    {
        "generate_shakespeare_x_post": "generate_shakespeare_x_post",
        "max_retry_exceeded_exit": "max_retry_exceeded_exit",
        "save_result": "save_result"
    },
)
graph.add_edge("complete", "save_result")
graph.add_edge("evaluate_x_post", "save_result")
graph.add_edge("max_retry_exceeded", "max_retry_exceeded_exit")
graph.add_edge("evaluate_x_post", "max_retry_exceeded_exit")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
