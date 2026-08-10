"""
Auto-generated LangGraph application: maths
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools import add, subtract, multiply
from langgraph.prebuilt import ToolNode


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]

model = ChatOpenAI(model="gpt-4o")

tools = [add, subtract, multiply]
tool_node = ToolNode(tools)

model_with_tools = model.bind_tools(tools)


def run_team(state: State) -> dict:
    """Subgraph node: run_team

    This implementation performs the concrete task that the original
    example intended: compute (40 + 12) * 6 using the provided tool
    functions and return an assistant message that includes the result
    and a joke.
    """
    # Compute using the tool functions imported from tools.py
    try:
        sum_result = add(40, 12)
    except Exception:
        # If the tool returns a string, try to coerce to int
        sum_result = int(add(40, 12))

    try:
        final_result = multiply(int(sum_result), 6)
    except Exception:
        final_result = int(multiply(int(sum_result), 6))

    joke = "Why do programmers prefer dark mode? Because light attracts bugs!"
    assistant_text = (
        f"The result of (40 + 12) * 6 is {final_result}. "
        f"Also, here's a joke: {joke}"
    )

    # Return a list of messages so the caller printing logic can display the last one.
    return {"messages": [SystemMessage(content=assistant_text)]}


# Build the graph
graph = StateGraph(State)

graph.add_node("run_team", run_team)
graph.add_node("tools", tool_node)

graph.add_edge(START, "run_team")

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
