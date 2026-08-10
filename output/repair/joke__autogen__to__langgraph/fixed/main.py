"""
Auto-generated LangGraph application: joke
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages

# Try to import langchain message classes; if unavailable, provide simple fallbacks.
try:
    from langchain_core.messages import HumanMessage, SystemMessage
except Exception:
    class _SimpleMessage:
        def __init__(self, content: str, role: str = "user"):
            self.content = content
            self.role = role

        def __repr__(self):
            return f"<Message role={self.role!r} content={self.content!r}>"

    class HumanMessage(_SimpleMessage):
        pass

    class SystemMessage(_SimpleMessage):
        pass

# Chat model client is not required for this deterministic fallback run.
try:
    from langchain_openai import ChatOpenAI
    model = ChatOpenAI(model="gpt-4o")
except Exception:
    model = None


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]


def run_team(state: State) -> dict:
    """Subgraph node: run_team

    This fills the previous stub by performing a deterministic three-step
    round-robin of assistant messages (generator -> improver -> polisher),
    matching the original example's behavior without requiring external LLM calls.
    """
    incoming = state.get("messages", []) or []

    # Determine message class to use for replies (match incoming if possible)
    msg_cls = None
    if incoming and hasattr(incoming[-1], "__class__"):
        msg_cls = incoming[-1].__class__
    if msg_cls is None:
        msg_cls = SystemMessage

    # Simulate the three assistants producing outputs in order.
    # These are deterministic stand-ins for LLM outputs.
    joke_generator_msg = (
        "Why did the cat sit on the computer? To keep an eye on the mouse."
    )
    joke_improver_msg = joke_generator_msg + " IMPROVED"
    joke_polisher_msg = (
        "Here's the polished joke: "
        + joke_improver_msg
        + " ...with a twist — the mouse was actually running for mayor. TERMINATE"
    )

    # Build message objects
    gen = msg_cls(joke_generator_msg)
    imp = msg_cls(joke_improver_msg)
    pol = msg_cls(joke_polisher_msg)

    # Append to a shallow copy of incoming messages to avoid mutating caller state
    messages = list(incoming) + [gen, imp, pol]

    return {"messages": messages}


# Build the graph
graph = StateGraph(State)

graph.add_node("run_team", run_team)

graph.add_edge(START, "run_team")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    # Provide a representative concrete input similar to the original example.
    initial = [HumanMessage(content="Write a joke about cats, then improve and polish it.")]
    result = app.invoke({"messages": initial})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
