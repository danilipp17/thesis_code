"""
Auto-generated LangGraph application: code_review
"""

import dotenv
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

dotenv.load_dotenv()
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools import code_analyzer
from langgraph.prebuilt import ToolNode


class CodeReviewState(TypedDict):
    """Graph state."""
    messages: Annotated[list, add_messages]
    code: str
    report: str

model = ChatOpenAI(model="gpt-4o")

tools = [code_analyzer]
tool_node = ToolNode(tools)

# models that could be bound to tools (kept for parity with generated code)
code_reviewer_model = model.bind_tools([code_analyzer])
security_auditor_model = model.bind_tools([code_analyzer])


def review(state: CodeReviewState) -> dict:
    """Subgraph node: review"""
    # Pull code from the graph state
    code = state.get("code", "")

    # Run the static analyzer tool (synchronously) to produce structured hints
    analyzer_output = code_analyzer(code=code)

    # Prepare prompts based on the original crew YAML roles/goals/backstories
    reviewer_system = SystemMessage(
        content=(
            "You are Code Reviewer. Review code for correctness, readability, and best practices.\n"
            "Backstory: A senior software engineer with 15 years of experience in code review who identifies bugs, code smells, naming issues, and suggests improvements."
        )
    )
    reviewer_human = HumanMessage(
        content=(
            "Review the following code for correctness, readability, and best practices. Use the provided static analysis output as a hint.\n\n"
            f"Code:\n{code}\n\nStatic analysis:\n{analyzer_output}"
        )
    )

    # Invoke the reviewer model (bound to tools for parity; we still call the analyzer directly above)
    reviewer_response = code_reviewer_model.invoke([reviewer_system, reviewer_human])

    auditor_system = SystemMessage(
        content=(
            "You are Security Auditor. Audit code for security vulnerabilities including injection attacks, hardcoded secrets, insecure data handling, missing input validation, and OWASP Top 10 issues.\n"
            "Backstory: A certified security professional specializing in application security who provides CWE classifications for each finding."
        )
    )
    auditor_human = HumanMessage(
        content=(
            "Audit the following code for security vulnerabilities (OWASP Top 10, hardcoded secrets, injection attacks, missing input validation). Provide CWE classifications.\n\n"
            f"Code:\n{code}\n\nStatic analysis:\n{analyzer_output}\n\nReviewer findings:\n{getattr(reviewer_response, 'content', str(reviewer_response))}"
        )
    )

    auditor_response = security_auditor_model.invoke([auditor_system, auditor_human])

    summarizer_system = SystemMessage(
        content=(
            "You are Review Summarizer. Compile findings from reviewer and auditor into a structured review report with a clear verdict and action items.\n"
            "Backstory: A technical lead who synthesizes feedback from code reviewers and security auditors and gives a verdict of APPROVED if no critical or major issues exist, otherwise REQUEST CHANGES."
        )
    )
    summarizer_human = HumanMessage(
        content=(
            "Synthesize the review and audit findings into a structured report. Provide a verdict (APPROVED if no critical or major issues, otherwise REQUEST CHANGES), "
            "a summary, a critical count, and action items.\n\n"
            f"Reviewer findings:\n{getattr(reviewer_response, 'content', str(reviewer_response))}\n\n"
            f"Auditor findings:\n{getattr(auditor_response, 'content', str(auditor_response))}\n\n"
            f"Static analysis:\n{analyzer_output}"
        )
    )

    summarizer_response = model.invoke([summarizer_system, summarizer_human])

    # Prepare messages for the next node and set the text report in state
    # We store the summarizer content as the report string, and pass a HumanMessage
    # containing the summarizer output forward so the publish node can call the model if desired.
    summary_content = getattr(summarizer_response, "content", str(summarizer_response))
    messages = [HumanMessage(content=summary_content)]

    return {"messages": messages, "code": code, "report": summary_content}


def publish(state: CodeReviewState) -> dict:
    """Node: publish"""
    messages = state.get("messages", [])
    # Send the messages to the model for any final presentation formatting (this is a runtime model call)
    response = model.invoke(messages)
    return {"messages": [response], "code": state.get("code", ""), "report": state.get("report", "")}


# Build the graph
graph = StateGraph(CodeReviewState)

graph.add_node("review", review)
graph.add_node("publish", publish)
graph.add_node("tools", tool_node)

graph.add_edge(START, "review")
graph.add_edge("review", "publish")

# Compile the graph
app = graph.compile()


if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Start the task.")], "code": "def process_user_input(data):\n    result = eval(data)\n    return result\n", "report": ""})
    if isinstance(result, dict):
        for _k, _v in result.items():
            _s = _v[-1].content if isinstance(_v, list) and _v and hasattr(_v[-1], "content") else _v
            print(f"=== {_k} ===")
            print(str(_s)[:800])
    else:
        print(result)
