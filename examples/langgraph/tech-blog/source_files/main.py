import os
from typing import TypedDict, Sequence, Annotated
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


class TechBlogState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    research: str
    draft: str
    final_post: str
    topic: str


def researcher(state: TechBlogState):
    llm = ChatOpenAI(model="gpt-4o")
    topic = state["topic"]
    prompt = (
        f"Research the following topic and provide a comprehensive summary: {topic}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"research": response.content}


def writer(state: TechBlogState):
    llm = ChatOpenAI(model="gpt-4o")
    research = state["research"]
    prompt = f"Using the following research, write a 500-word engaging tech blog post:\n\n{research}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"draft": response.content}


def editor(state: TechBlogState):
    llm = ChatOpenAI(model="gpt-4o")
    draft = state["draft"]
    prompt = f"Review the following drafted blog post. Fix any grammatical errors, improve the flow, and return the final polished version ready for publishing:\n\n{draft}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"final_post": response.content}


def should_end(state: TechBlogState):
    return "end"


graph = StateGraph(TechBlogState)
graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_node("editor", editor)

graph.set_entry_point("researcher")
graph.add_edge("researcher", "writer")
graph.add_edge("writer", "editor")
graph.add_edge("editor", END)

app = graph.compile()


def run():
    print("Starting LangGraph Tech Blog Generation...")
    initial_state = {
        "messages": [],
        "topic": "Agentic AI Frameworks",
        "research": "",
        "draft": "",
        "final_post": "",
    }
    result = app.invoke(initial_state)
    print("Completed!")
    print(result["final_post"])


if __name__ == "__main__":
    run()
