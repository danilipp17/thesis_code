"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()


class CodeReviewState(BaseModel):
    """Flow state — customize fields as needed."""
    audit: str = ""
    code: str = ""
    messages: list = []
    review: str = ""
    summary: str = ""


class StateGraph(Flow[CodeReviewState]):

    @start()
    def code_reviewer(self):
        pass  # TODO: implement step logic

    @listen(code_reviewer)
    def security_auditor(self):
        pass  # TODO: implement step logic

    @listen(security_auditor)
    def review_summarizer(self):
        pass  # TODO: implement step logic


def kickoff():
    """
    Run the three-step code review flow inline.

    We perform real LLM calls (via langchain_openai.ChatOpenAI) and call the
    static analyzer from tools.code_analyzer. The function drives the same
    logical sequence as the generated StateGraph: reviewer -> auditor ->
    summarizer, and prints the outputs.
    """
    # Local imports so we only modify function body (keeps top-level import structure)
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI
    from tools import code_analyzer

    # Concrete code to review (same representative sample used by the original LangGraph example)
    CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""

    # Initialize state
    state = CodeReviewState(code=CODE_TO_REVIEW, review="", audit="", summary="")

    # Step 1: Code reviewer
    llm = ChatOpenAI(model="gpt-4o")
    analysis = code_analyzer(state.code)
    prompt_reviewer = (
        "You are a senior software engineer with 15 years of experience "
        "in code review. Review the following code for correctness, "
        "readability, and best practices. Identify bugs, code smells, "
        "naming issues, and suggest improvements.\n\n"
        f"Code:\n{state.code}\n\nAnalyzer output:\n{analysis}"
    )
    resp = llm.invoke([HumanMessage(content=prompt_reviewer)])
    state.review = resp.content

    # Step 2: Security auditor
    llm2 = ChatOpenAI(model="gpt-4o")
    analysis2 = code_analyzer(state.code)
    prompt_auditor = (
        "You are a certified security professional specializing in "
        "application security. Audit the following code for OWASP Top "
        "10 issues, hardcoded secrets, injection attacks, and missing "
        "input validation. Provide CWE classifications.\n\n"
        f"Code:\n{state.code}\n\nAnalyzer output:\n{analysis2}"
    )
    resp2 = llm2.invoke([HumanMessage(content=prompt_auditor)])
    state.audit = resp2.content

    # Step 3: Review summarizer
    llm3 = ChatOpenAI(model="gpt-4o")
    prompt_summarizer = (
        "You are a technical lead. Synthesize the following review and "
        "audit findings into a structured report. Provide a verdict of "
        "APPROVED if no critical or major issues, otherwise REQUEST "
        "CHANGES. Include a summary, critical count, and action items.\n\n"
        f"Review:\n{state.review}\n\nAudit:\n{state.audit}"
    )
    resp3 = llm3.invoke([HumanMessage(content=prompt_summarizer)])
    state.summary = resp3.content

    # Print results (must be printed as the program's output)
    print("Starting CrewAI Code Review...\n")
    print("\n=== Code Review ===\n")
    print(state.review)
    print("\n=== Security Audit ===\n")
    print(state.audit)
    print("\n=== Summary ===\n")
    print(state.summary)


if __name__ == "__main__":
    kickoff()
