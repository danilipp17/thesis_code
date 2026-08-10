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


class TechBlogState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    final_post: str
    topic: str

model = ChatOpenAI(model="gpt-4o")


def write_blog(state: TechBlogState) -> dict:
    """Subgraph node: write_blog
    Simulates the TechBlogCrew: researcher -> writer -> editor.
    Produces a research summary, a draft post, and a final edited post.
    Returns updated messages (as HumanMessage instances) and final_post.
    """
    topic = state.get("topic", "Agentic AI Frameworks")

    # Researcher output (concise structured research summary)
    research = (
        f"Research Summary on '{topic}':\n\n"
        "- Key trends: Increased adoption of agentic architectures, modular pipelines, "
        "and better tooling for multi-agent coordination.\n"
        "- Benefits: Improved automation of complex workflows, better scalability, and "
        "specialized agents that can collaborate to solve tasks.\n"
        "- Challenges: Safety/alignment concerns, integration complexity, debugging distributed agents, "
        "and data privacy.\n"
        "- Future outlook: Expect tighter integration with enterprise tooling, more robust evaluation "
        "benchmarks, and clearer best practices for governance.\n"
    )

    # Writer output (blog draft based on the research)
    draft = (
        f"{topic}: The Rise of Agentic AI\n\n"
        "Agentic AI frameworks are transforming how we build autonomous systems. They enable multiple "
        "specialized components to work together—each handling planning, perception, or execution—so "
        "that complex tasks can be decomposed and solved more reliably. Recent trends include the move "
        "toward modular agent architectures, improved cross-agent communication protocols, and richer "
        "developer tooling that streamlines orchestration.\n\n"
        "The primary benefits are clear: greater task automation, scalability across different problem "
        "domains, and the ability to mix-and-match agents for bespoke workflows. However, this comes "
        "with non-trivial challenges. Ensuring safe and aligned behavior across several cooperating agents "
        "is harder than for single-model systems. Integration and observability remain engineering hurdles, "
        "and organizations must be mindful of data governance when agents access multiple data sources.\n\n"
        "Looking forward, the agentic AI ecosystem will likely see more standardization around agent "
        "interfaces and protocols, stronger evaluation suites for multi-agent behavior, and tighter "
        "enterprise integration that emphasizes reliability and compliance."
    )

    # Editor output (polished final post)
    edited = (
        f"{topic} — A Practical Overview\n\n"
        + draft
        + "\n\nEdited for clarity and flow: This article highlights why agentic AI is gaining traction, "
        "what practitioners should watch out for, and how teams can prepare. Start small with clear "
        "interfaces between agents, prioritize observability to debug interactions, and adopt strong "
        "safety checks before deploying agentic systems in production."
    )

    messages = [
        HumanMessage(content=research),
        HumanMessage(content=draft),
        HumanMessage(content=edited),
    ]

    return {"messages": messages, "final_post": edited}


def publish(state: TechBlogState) -> dict:
    """Node: publish
    Finalizes the output for publication. Appends a publication system message and
    returns the final messages and final_post.
    """
    messages = state.get("messages", []) or []
    final_post = state.get("final_post", "")
    topic = state.get("topic", "Agentic AI Frameworks")

    published_message = SystemMessage(
        content=f"Published blog post on '{topic}':\n\n{final_post}"
    )

    return {"messages": messages + [published_message], "final_post": final_post}


# Build the graph
graph = StateGraph(TechBlogState)

graph.add_node("write_blog", write_blog)
graph.add_node("publish", publish)

graph.add_edge(START, "write_blog")
graph.add_edge("write_blog", "publish")
graph.add_edge("publish", END)

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "final_post": "", "topic": "Agentic AI Frameworks"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
