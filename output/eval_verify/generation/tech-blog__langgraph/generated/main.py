"""
Auto-generated LangGraph application: tech_blog
"""

import dotenv
from typing import Annotated, Sequence, TypedDict
import operator

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


class TechBlogState(TypedDict):
    """Graph state."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    draft: str
    final_post: str
    research: str
    topic: str

model = ChatOpenAI(model="gpt-4o")


def researcher(state: TechBlogState) -> dict:
    """Node: researcher"""
    topic = state.get('topic', '')
    task_prompt = f'Research the following topic and provide a comprehensive summary: {topic}'
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"research": response.content}


def writer(state: TechBlogState) -> dict:
    """Node: writer"""
    research = state.get('research', '')
    task_prompt = f'Using the following research, write a 500-word engaging tech blog post:\n\n{research}'
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"draft": response.content}


def editor(state: TechBlogState) -> dict:
    """Node: editor"""
    draft = state.get('draft', '')
    task_prompt = f'Review the following drafted blog post. Fix any grammatical errors, improve the flow, and return the final polished version ready for publishing:\n\n{draft}'
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"final_post": response.content}


# Build the graph
graph = StateGraph(TechBlogState)

graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_node("editor", editor)

graph.add_edge(START, "researcher")
graph.add_edge("researcher", "writer")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "draft": "sample draft", "final_post": "sample final_post", "research": "sample research", "topic": "sample topic"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
