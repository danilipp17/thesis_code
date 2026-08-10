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


class MathsState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    answer: str
    query: str

model = ChatOpenAI(model="gpt-4o")

tools = [add, subtract, multiply]
tool_node = ToolNode(tools)

# model_with_tools left in place if needed by environment; not required for this flow
try:
    model_with_tools = model.bind_tools(tools)
except Exception:
    model_with_tools = None


def reason_and_act(state: MathsState) -> dict:
    """Subgraph node: reason_and_act

    Prepares the system and user messages (injecting the real query) and
    returns them so the downstream publish node can invoke the model.
    """
    query = state.get("query", "") or ""
    system_content = (
        "Maths Reasoning Assistant\n"
        "You are an AI assistant that answers user queries to the best of your ability, "
        "using the available tools whenever a step requires computation."
    )
    system_msg = SystemMessage(content=system_content)
    human_msg = HumanMessage(
        content=(
            f"Answer the following user query, using the available arithmetic tools whenever "
            f"a step requires computation: {query}"
        )
    )
    # Return the prepared conversation messages for the publish node to invoke the model.
    return {"messages": [system_msg, human_msg], "query": query}


def publish(state: MathsState) -> dict:
    """Node: publish

    Invokes the language model with the prepared messages and stores the model's
    response in state['answer'] and returns the response as the messages list.
    """
    messages = state.get("messages", []) or []
    # Invoke the model with the messages prepared by reason_and_act.
    response = model.invoke(messages)
    # Try to extract content if present, otherwise stringify the response
    content = getattr(response, "content", None)
    if content is None:
        try:
            content = str(response)
        except Exception:
            content = ""
    return {"messages": [response], "answer": content}


# Build the graph
graph = StateGraph(MathsState)

graph.add_node("reason_and_act", reason_and_act)
graph.add_node("publish", publish)
graph.add_node("tools", tool_node)

graph.add_edge(START, "reason_and_act")
graph.add_edge("reason_and_act", "publish")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    # Provide a representative concrete input similar to the original example.
    result = app.invoke({
        "messages": [HumanMessage(content="Start the task.")],
        "answer": "",
        "query": "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."
    })
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
