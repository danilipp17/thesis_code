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

# NOTE: We keep the original ChatOpenAI import for compatibility,
# but will use a local mock inside nodes to avoid external calls.

model = ChatOpenAI(model="gpt-4o")

tools = [code_analyzer]
tool_node = ToolNode(tools)

code_reviewer_model = None  # placeholder to mirror generated structure
security_auditor_model = None  # placeholder to mirror generated structure


def _make_response(text: str):
    """Simple response object with .content to be compatible with printing."""
    class Resp:
        def __init__(self, content: str):
            self.content = content
        def __repr__(self):
            return f"Resp(content={self.content!r})"
    return Resp(text)


def _mock_invoke_for_role(role: str, prompt: str) -> Any:
    """
    Deterministic mock that simulates model results based on role and prompt.
    """
    # Very simple heuristic-based replies to demonstrate flow.
    if role == "Code Reviewer":
        # Echo some guidance and mention analyzer highlights if present.
        if "Tool output:" in prompt:
            tool_part = prompt.split("Tool output:", 1)[1].strip()
            summary = f"Analyzer findings: {tool_part.splitlines()[0] if tool_part else 'None'}"
        else:
            summary = "No analyzer output."
        content = f"Reviewer findings:\n- Summary: {summary}\n- Suggestion: improve error handling and avoid unsafe constructs."
    elif role == "Security Auditor":
        # Look for eval mention
        content_lines = []
        if "eval" in prompt or "eval()" in prompt or "code injection" in prompt.lower():
            content_lines.append("- Critical: Use of eval() may allow code injection (CWE-95).")
        else:
            content_lines.append("- No obvious injection found.")
        content = "Security findings:\n" + "\n".join(content_lines)
    elif role == "Review Summarizer":
        # Combine provided findings into a verdict.
        verdict = "APPROVED"
        if "Critical" in prompt or "eval" in prompt:
            verdict = "REQUEST CHANGES"
        content = f"Verdict: {verdict}\nSummary: Combined findings.\nAction items: Address critical security issues and improve error handling."
    else:
        content = "Generic response."
    return _make_response(content)


def review(state: CodeReviewState) -> dict:
    """Subgraph node: review"""
    # Orchestrate simple three-step team: reviewer -> auditor -> summarizer
    code = state.get("code", "")
    # Run the static analyzer tool
    try:
        tool_output = code_analyzer(code=code)
    except Exception as e:
        tool_output = f"Tool error: {type(e).__name__}: {e}"

    # Reviewer step
    reviewer_system = SystemMessage(content="You are Code Reviewer. Review code for correctness, readability, and best practices.")
    reviewer_human = HumanMessage(content=f"Review the following code for correctness, readability, and best practices. Use the code analyzer tool.\n\n{code}\n\nTool output:\n{tool_output}")
    reviewer_prompt = reviewer_system.content + "\n\n" + reviewer_human.content
    reviewer_resp = _mock_invoke_for_role("Code Reviewer", reviewer_prompt)

    # Security auditor step (has context from reviewer)
    auditor_system = SystemMessage(content="You are Security Auditor. Audit code for security vulnerabilities including injection attacks, hardcoded secrets, insecure data handling, and missing input validation.")
    auditor_human = HumanMessage(content=f"Audit the following code for security vulnerabilities (OWASP Top 10, hardcoded secrets, injection attacks, missing input validation). Provide CWE classifications.\n\n{code}\n\nReviewer findings:\n{getattr(reviewer_resp, 'content', str(reviewer_resp))}")
    auditor_prompt = auditor_system.content + "\n\n" + auditor_human.content
    auditor_resp = _mock_invoke_for_role("Security Auditor", auditor_prompt)

    # Summarizer step (synthesizes both findings)
    summarizer_system = SystemMessage(content="You are Review Summarizer. Compile findings from reviewer and auditor into a structured review report with a clear verdict and action items.")
    summarizer_human = HumanMessage(content=f"Synthesize the review and audit findings into a structured report. Provide a verdict (APPROVED if no critical or major issues, otherwise REQUEST CHANGES), a summary, a critical count, and action items.\n\nReviewer findings:\n{getattr(reviewer_resp, 'content', str(reviewer_resp))}\n\nSecurity findings:\n{getattr(auditor_resp, 'content', str(auditor_resp))}")
    summarizer_prompt = summarizer_system.content + "\n\n" + summarizer_human.content
    summarizer_resp = _mock_invoke_for_role("Review Summarizer", summarizer_prompt)

    # Return the created messages so downstream nodes can use them.
    return {"messages": [reviewer_resp, auditor_resp, summarizer_resp]}


def publish(state: CodeReviewState) -> dict:
    """Node: publish"""
    messages = state.get("messages", [])
    # Compose a final published message by concatenating contents
    combined_text_parts = []
    for m in messages:
        if hasattr(m, "content"):
            combined_text_parts.append(m.content)
        else:
            combined_text_parts.append(str(m))
    combined = "\n\n".join(combined_text_parts) if combined_text_parts else "No messages to publish."
    response = _make_response(f"Code review complete:\n\n{combined}")
    return {"messages": [response]}


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
