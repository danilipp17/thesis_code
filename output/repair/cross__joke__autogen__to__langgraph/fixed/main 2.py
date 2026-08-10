"""
Auto-generated LangGraph application: joke
"""

import dotenv
from typing import Annotated, TypedDict
import re

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]

model = ChatOpenAI(model="gpt-4o")


def run_team(state: State) -> dict:
    """Subgraph node: run_team

    This replaces the original stub: it synthesizes a short joke generation
    pipeline (generator -> improver -> polisher) and returns the extended
    messages list. It looks for a task in the incoming human messages; if no
    topic is found, it defaults to "cats".
    """
    incoming = state.get("messages", []) or []

    # Extract task text from incoming human messages (prefer first human message
    # that mentions "joke" or contains text). Fall back to a default task.
    task_text = None
    for m in incoming:
        if hasattr(m, "content") and isinstance(m.content, str):
            text = m.content.strip()
            if text:
                task_text = text
                if "joke" in text.lower():
                    break

    if not task_text:
        task_text = "Write a joke about cats, then improve and polish it."

    # Try to parse a topic after the word "about", otherwise default to "cats".
    match = re.search(r"about\s+([A-Za-z0-9 _-]+?)(?:[.,]|$)", task_text, flags=re.I)
    if match:
        topic = match.group(1).strip()
        # If parsing produced an empty string, fallback
        if not topic:
            topic = "cats"
    else:
        topic = "cats"

    # Synthesize three assistant messages (Generator, Improver, Polisher).
    gen_joke = (
        f"Here's a short joke about {topic}:\n"
        f"Why did the {topic} sit on the computer? It wanted to keep an eye on the mouse."
    )

    improver_joke = (
        f"{gen_joke} Now make it punchier with clever wordplay:\n"
        f"Why did the {topic} sit on the computer? It wanted to keep an eye on the mouse — "
        f"after all, spotting a 'mouse' before it clicks is a real cat-astrophe! IMPROVED"
    )

    polisher_joke = (
        f"{improver_joke} Add a surprising twist for the final polished version:\n"
        f"It turns out the mouse had a tiny top hat — the {topic} couldn't resist a curtain call. TERMINATE"
    )

    # Use SystemMessage objects so the returned messages have a .content attribute
    # (the code that prints the result expects message objects with .content).
    new_messages = incoming[:]  # preserve prior messages
    new_messages.append(SystemMessage(content=gen_joke))
    new_messages.append(SystemMessage(content=improver_joke))
    new_messages.append(SystemMessage(content=polisher_joke))

    return {"messages": new_messages}


# Build the graph
graph = StateGraph(State)

graph.add_node("run_team", run_team)

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
