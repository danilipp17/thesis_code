"""
Auto-generated LangGraph application: code_review
"""

import dotenv
from typing import Annotated, Sequence, TypedDict
import operator

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


class CodeReviewState(TypedDict):
    """Graph state."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    audit: str
    code: str
    review: str
    summary: str

model = ChatOpenAI(model="gpt-4o")


def code_reviewer(state: CodeReviewState) -> dict:
    """Review the code for correctness, readability, and best practices."""
    analysis = state.get('analysis', '')
    task_prompt = f"You are a senior software engineer with 15 years of experience in code review. Review the following code for correctness, readability, and best practices. Identify bugs, code smells, naming issues, and suggest improvements.\n\nCode:\n{state['code']}\n\nAnalyzer output:\n{analysis}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"review": response.content}


def security_auditor(state: CodeReviewState) -> dict:
    """Audit the code for security vulnerabilities with CWE classifications."""
    analysis = state.get('analysis', '')
    task_prompt = f"You are a certified security professional specializing in application security. Audit the following code for OWASP Top 10 issues, hardcoded secrets, injection attacks, and missing input validation. Provide CWE classifications.\n\nCode:\n{state['code']}\n\nAnalyzer output:\n{analysis}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"audit": response.content}


def review_summarizer(state: CodeReviewState) -> dict:
    """Synthesize review and audit findings into a structured report."""
    task_prompt = f"You are a technical lead. Synthesize the following review and audit findings into a structured report. Provide a verdict of APPROVED if no critical or major issues, otherwise REQUEST CHANGES. Include a summary, critical count, and action items.\n\nReview:\n{state['review']}\n\nAudit:\n{state['audit']}"
    messages = state.get("messages", []) + [HumanMessage(content=task_prompt)]
    response = model.invoke(messages)
    return {"summary": response.content}


# Build the graph
graph = StateGraph(CodeReviewState)

graph.add_node("code_reviewer", code_reviewer)
graph.add_node("security_auditor", security_auditor)
graph.add_node("review_summarizer", review_summarizer)

graph.add_edge(START, "code_reviewer")
graph.add_edge("code_reviewer", "security_auditor")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "audit": "sample audit", "code": "sample code", "review": "sample review", "summary": "sample summary"})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
