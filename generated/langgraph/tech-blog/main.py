"""
Auto-generated LangGraph application: tech-blog
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


class State(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    research: str
    draft: str
    final_post: str
    topic: str

model = ChatOpenAI(model="gpt-4o")


def researcher(state: State) -> dict:
    """Node: researcher"""
    topic = state.get('topic', 'agentic ai')
    task_prompt = f'Research the following topic and provide a comprehensive summary: {topic}'
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"research": response.content}


def writer(state: State) -> dict:
    """Node: writer"""
    research = state.get('research', '')
    task_prompt = f'Using the following research, write a 500-word engaging tech blog post:\n\n{research}'
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"draft": response.content}


def editor(state: State) -> dict:
    """Node: editor"""
    draft = state.get('draft', '')
    task_prompt = f'Review the following drafted blog post. Fix any grammatical errors, improve the flow, and return the final polished version ready for publishing:\n\n{draft}'
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"final_post": response.content}


# Build the graph
graph = StateGraph(State)

graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_node("editor", editor)

graph.add_edge(START, "researcher")
graph.add_edge("researcher", "writer")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": ["Agenti AI Frameworks"]})
    print(result["messages"][-1].content)
