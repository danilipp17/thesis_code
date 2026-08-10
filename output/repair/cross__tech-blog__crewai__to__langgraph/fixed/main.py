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

    Implements the TechBlogCrew workflow:
      1) Researcher produces research on the topic.
      2) Writer produces a ~500-word draft using the research.
      3) Editor refines the draft into the final post.

    Each step invokes the LLM at runtime. The actual outputs are not
    hardcoded and will vary between runs.
    """
    topic = state.get("topic", "Agentic AI Frameworks")

    # Researcher step
    sys_research = SystemMessage(
        content=(
            "Senior Tech Researcher — An expert researcher skilled at finding the latest "
            "technological trends and summarizing them clearly."
        )
    )
    human_research = HumanMessage(
        content=(
            f"Gather comprehensive, up-to-date information on '{topic}'. "
            "Identify key trends, benefits, challenges, and future outlook. "
            "Provide a detailed summary of your findings."
        )
    )
    research_response = model.invoke([sys_research, human_research])

    # Extract research text safely from the model response
    research_text = getattr(research_response, "content", None)
    if research_text is None:
        try:
            # try common alternatives
            research_text = research_response[0].content  # type: ignore
        except Exception:
            research_text = str(research_response)

    # Writer step
    sys_writer = SystemMessage(
        content=(
            "Tech Blog Writer — A seasoned technical writer who can make complex topics "
            "accessible to a broad audience."
        )
    )
    human_writer = HumanMessage(
        content=(
            f"Using the research provided below, write a comprehensive ~500-word blog post about '{topic}'.\n\n"
            f"Research:\n{research_text}\n\nWrite an engaging, easy-to-read post aimed at a broad technical audience."
        )
    )
    draft_response = model.invoke([sys_writer, human_writer])

    draft_text = getattr(draft_response, "content", None)
    if draft_text is None:
        try:
            draft_text = draft_response[0].content  # type: ignore
        except Exception:
            draft_text = str(draft_response)

    # Editor step
    sys_editor = SystemMessage(
        content=(
            "Content Editor — A meticulous editor with a keen eye for detail, ensuring every published piece is top-notch."
        )
    )
    human_editor = HumanMessage(
        content=(
            "Review the drafted blog post below. Check for clarity, tone, spelling, and grammar. Ensure it is engaging "
            "and ready for publication. Provide a polished final version.\n\n"
            f"Draft:\n{draft_text}"
        )
    )
    final_response = model.invoke([sys_editor, human_editor])

    final_text = getattr(final_response, "content", None)
    if final_text is None:
        try:
            final_text = final_response[0].content  # type: ignore
        except Exception:
            final_text = str(final_response)

    # Store the sequence of responses (research, draft, final) in messages
    messages = [research_response, draft_response, final_response]

    return {"messages": messages, "final_post": final_text, "topic": topic}


def publish(state: TechBlogState) -> dict:
    """Node: publish

    Print the final post (produced by the crew) and pass state through.
    """
    final_post = state.get("final_post", "")
    print("Tech blog complete:")
    print(final_post)
    # Keep messages and topic unchanged
    return {
        "messages": state.get("messages", []),
        "final_post": final_post,
        "topic": state.get("topic", ""),
    }


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
