"""
code-review — LangGraph port of the AutoGen original.

Original: examples/autogen/code-review/source_files/main.py — three
AssistantAgents in RoundRobinGroupChat with a shared FunctionTool.

LangGraph mapping:
  - RoundRobinGroupChat   -> StateGraph with linear edges
  - 3 AssistantAgents     -> 3 node functions
  - FunctionTool          -> plain Python helper called inside the
                              reviewer and auditor nodes (the LLM
                              receives the analyzer output as context
                              in the prompt rather than tool-calling)
  - implicit chat passing -> explicit TypedDict state fields
                              (code, review, audit, summary)
"""

import operator
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from tools import code_analyzer

load_dotenv()


CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""


class CodeReviewState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    code: str
    review: str
    audit: str
    summary: str


def code_reviewer(state: CodeReviewState):
    """Review the code for correctness, readability, and best practices."""
    llm = ChatOpenAI(model="gpt-4o")
    analysis = code_analyzer(state["code"])
    prompt = (
        "You are a senior software engineer with 15 years of experience "
        "in code review. Review the following code for correctness, "
        "readability, and best practices. Identify bugs, code smells, "
        "naming issues, and suggest improvements.\n\n"
        f"Code:\n{state['code']}\n\nAnalyzer output:\n{analysis}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"review": response.content}


def security_auditor(state: CodeReviewState):
    """Audit the code for security vulnerabilities with CWE classifications."""
    llm = ChatOpenAI(model="gpt-4o")
    analysis = code_analyzer(state["code"])
    prompt = (
        "You are a certified security professional specializing in "
        "application security. Audit the following code for OWASP Top "
        "10 issues, hardcoded secrets, injection attacks, and missing "
        "input validation. Provide CWE classifications.\n\n"
        f"Code:\n{state['code']}\n\nAnalyzer output:\n{analysis}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"audit": response.content}


def review_summarizer(state: CodeReviewState):
    """Synthesize review and audit findings into a structured report."""
    llm = ChatOpenAI(model="gpt-4o")
    prompt = (
        "You are a technical lead. Synthesize the following review and "
        "audit findings into a structured report. Provide a verdict of "
        "APPROVED if no critical or major issues, otherwise REQUEST "
        "CHANGES. Include a summary, critical count, and action items.\n\n"
        f"Review:\n{state['review']}\n\nAudit:\n{state['audit']}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"summary": response.content}


graph = StateGraph(CodeReviewState)
graph.add_node("code_reviewer", code_reviewer)
graph.add_node("security_auditor", security_auditor)
graph.add_node("review_summarizer", review_summarizer)

graph.set_entry_point("code_reviewer")
graph.add_edge("code_reviewer", "security_auditor")
graph.add_edge("security_auditor", "review_summarizer")
graph.add_edge("review_summarizer", END)

app = graph.compile()


def run():
    print("Starting LangGraph Code Review...")
    initial_state = {
        "messages": [],
        "code": CODE_TO_REVIEW,
        "review": "",
        "audit": "",
        "summary": "",
    }
    result = app.invoke(initial_state)
    print("\n=== Code Review ===\n")
    print(result["review"])
    print("\n=== Security Audit ===\n")
    print(result["audit"])
    print("\n=== Summary ===\n")
    print(result["summary"])


if __name__ == "__main__":
    run()
