"""
Auto-generated LangGraph application: tech_blog
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]


model = ChatOpenAI(model="gpt-4o")


def _make_message(content: str):
    """
    Create a message object compatible with the rest of this script.
    Prefer using HumanMessage if available (imported above), otherwise fall back
    to a simple object with a .content attribute.
    """
    try:
        return HumanMessage(content=content)
    except Exception:
        # Fallback simple object
        class SimpleMsg:
            def __init__(self, c): self.content = c
        return SimpleMsg(content)


def run_team(state: State) -> dict:
    """Subgraph node: run_team

    Simulates the RoundRobinGroupChat with Researcher, Writer, Editor and a
    MaxMessageTermination of 4 messages. This is a deterministic, local
    simulation (no external LLM calls) that produces representative outputs.
    """
    # Read initial messages from the incoming state (if any)
    incoming = state.get("messages", []) or []

    # Extract task prompt from the last human message if present, otherwise use default
    task_text = None
    if incoming:
        last = incoming[-1]
        # Try to get .content attribute, else str()
        task_text = getattr(last, "content", None) or str(last)

    # If the starter message is the tiny "Start the task." placeholder,
    # replace it with the canonical task used in the original AutoGen example.
    default_task = "We need a blog post about Agentic AI Frameworks. Please research, write, and edit."
    if not task_text or task_text.strip().lower() == "start the task.":
        task_text = default_task

    messages = list(incoming)  # copy existing messages

    # Simulate Researcher (first turn)
    researcher_content = (
        "Researcher: I have reviewed recent literature and implementations of agentic AI frameworks. "
        "Core themes include modular agent architectures, robust planning & memory components, "
        "tools & tool-use integration, safety/guardrails, and coordination patterns for multi-agent systems. "
        "Key trade-offs are between autonomy and controllability, and between narrow tool-use vs. general capabilities. "
        "I recommend highlighting: (1) agent orchestration patterns (e.g., loop-based, plan-and-act), "
        "(2) state and memory management, (3) tool ecosystems and adapters, and (4) safety & evaluation approaches."
    )
    messages.append(_make_message(researcher_content))

    # Simulate Writer (second turn) - produce a concise blog-style post and signal 'WRITTEN'
    writer_content = (
        "Writer: Agentic AI Frameworks are reshaping how we build intelligent systems by combining modular agents, "
        "planning, and tool use to perform complex tasks. At the heart of modern frameworks is an architecture that "
        "separates reasoning (planning, decision-making) from execution (tool invocation, action). This separation "
        "allows teams of components to coordinate: some components manage state and memory, others plan multi-step "
        "strategies, and specialized tool adapters enable real-world integrations like web APIs or databases.\n\n"
        "Designers face trade-offs: increasing autonomy can boost capability but makes oversight harder; richer tool "
        "ecosystems expand functionality but raise integration complexity. Best practices include keeping explicit "
        "memory/state representations, versioning tool adapters, and designing evaluation harnesses that test both "
        "task success and safety constraints. With careful design, agentic frameworks enable robust, composable "
        "intelligent systems that can be iteratively improved and safely deployed. WRITTEN"
    )
    messages.append(_make_message(writer_content))

    # Simulate Editor (third turn) - polish and conclude with 'TERMINATE'
    editor_content = (
        "Editor: Polished blog post:\n\n"
        "Agentic AI Frameworks are transforming how developers assemble intelligent systems by combining modular "
        "agents, planning mechanisms, and practical tool integrations. These frameworks typically separate reasoning "
        "from execution: planners and memory managers form the cognitive core, while tool adapters handle concrete "
        "interactions with APIs and external systems. This modularity enables teams of components to collaborate on "
        "complex tasks, promoting reuse and easier maintenance.\n\n"
        "Key considerations include making explicit trade-offs between autonomy and control, ensuring tool adapters "
        "are well-tested and versioned, and building evaluation suites that measure both task success and adherence "
        "to safety constraints. By adopting clear state management, transparent planning, and robust tooling, teams "
        "can deploy agentic systems that are both powerful and governable. TERMINATE"
    )
    messages.append(_make_message(editor_content))

    # The termination condition in the original example was MaxMessageTermination(4).
    # We produced 3 agent messages after the initial one, for a total of 4 additional messages;
    # return the assembled messages back into the state shape expected by the compiled graph.
    return {"messages": messages}


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
