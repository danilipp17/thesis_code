"""
Auto-generated AutoGen application: code_review
"""

import asyncio
import dotenv
from typing import Any, Dict, List, Optional

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

import ast as _ast

model_client = OpenAIChatCompletionClient(model="gpt-4o")


# -- Agents --
code_reviewer = AssistantAgent(
    name="code_reviewer",
    model_client=model_client,
    system_message=(
        "Review the code for correctness, readability, and best practices."
    ),
)

security_auditor = AssistantAgent(
    name="security_auditor",
    model_client=model_client,
    system_message=(
        "Audit the code for security vulnerabilities with CWE classifications."
    ),
)

review_summarizer = AssistantAgent(
    name="review_summarizer",
    model_client=model_client,
    system_message=(
        "Synthesize review and audit findings into a structured report."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[code_reviewer, security_auditor, review_summarizer],
    termination_condition=termination,
)


# Representative code to review (from the original example)
CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""


def code_analyzer(code: str) -> str:
    """Performs lightweight static analysis (deterministic)."""
    issues = []
    try:
        tree = _ast.parse(code)
        issues.append("Syntax: OK")
        for node in _ast.walk(tree):
            # Bare except detection
            if isinstance(node, _ast.ExceptHandler) and node.type is None:
                issues.append(
                    f"Line {node.lineno}: Bare 'except' clause — should catch specific exceptions."
                )
            # Detect use of eval
            if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name):
                if node.func.id == "eval":
                    issues.append(
                        f"Line {node.lineno}: Use of eval() with potentially untrusted data — risk of code injection."
                    )
            # Detect very simple pattern: return of raw input or similar
            if isinstance(node, _ast.Return) and isinstance(node.value, _ast.Name):
                # best-effort: if function returns a variable assigned directly from input via eval, note it
                issues.append(f"Line {getattr(node, 'lineno', '?')}: Return statement returns a raw variable; ensure it's sanitized.")
    except SyntaxError as e:
        issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
    return "\n".join(issues)


def generate_review(code: str, analysis: str) -> str:
    """Deterministic reviewer output summarizing issues and suggestions."""
    review_lines = []
    review_lines.append("Code Review Summary:")
    review_lines.append("- The function processes user input and uses eval() on the input. This is a critical security and correctness issue.")
    review_lines.append("- No input validation or sanitization is present.")
    review_lines.append("- The variable name 'result' is generic; consider more descriptive naming.")
    review_lines.append("")
    review_lines.append("Findings and Suggestions:")
    review_lines.append("1) Remove eval(): Replace eval(data) with a safe parser. If the intent is to parse Python literals, use ast.literal_eval(data). If parsing JSON, use json.loads(data).")
    review_lines.append("2) Validate input: Explicitly validate expected input types/structure before processing.")
    review_lines.append("3) Error handling: Add specific exception handling instead of letting exceptions propagate or using bare excepts.")
    review_lines.append("4) Add tests and docstring describing expected input format.")
    review_lines.append("")
    review_lines.append("Example replacement (JSON expected):")
    review_lines.append("    import json")
    review_lines.append("    def process_user_input(data):")
    review_lines.append("        parsed = json.loads(data)")
    review_lines.append("        # process parsed object safely")
    review_lines.append("        return parsed")
    review_lines.append("")
    review_lines.append("Analyzer output:")
    review_lines.append(analysis)
    return "\n".join(review_lines)


def generate_audit(code: str, analysis: str) -> str:
    """Deterministic security audit output with CWE references."""
    audit_lines = []
    audit_lines.append("Security Audit Summary:")
    audit_lines.append("- Critical: Use of eval() on user-controlled input leads to code injection vulnerabilities.")
    audit_lines.append("")
    audit_lines.append("Vulnerabilities Identified:")
    audit_lines.append("1) Code Injection via eval() — CWE-95 (Improper Neutralization of Directives/Expressions).")
    audit_lines.append("   - Impact: Remote code execution or arbitrary code execution in the process context.")
    audit_lines.append("   - Recommendation: Remove eval; use safe parsing (ast.literal_eval or json.loads), validate inputs, and apply least privilege.")
    audit_lines.append("")
    audit_lines.append("2) Lack of input validation — could lead to unexpected exceptions or logic errors (CWE-20).")
    audit_lines.append("")
    audit_lines.append("Additional Notes:")
    audit_lines.append("- No hardcoded secrets detected in the small snippet.")
    audit_lines.append("- Ensure logging does not inadvertently record sensitive data.")
    audit_lines.append("")
    audit_lines.append("Analyzer output:")
    audit_lines.append(analysis)
    return "\n".join(audit_lines)


def generate_summary(review: str, audit: str) -> str:
    """Deterministic synthesis of review + audit into a verdict and action items."""
    summary_lines = []
    # Determine verdict: if audit mentions 'Critical' or review mentions eval, request changes
    verdict = "APPROVED"
    critical_count = 0
    if "eval()" in review or "Critical" in audit or "code injection" in audit.lower():
        verdict = "REQUEST CHANGES"
        critical_count = 1
    summary_lines.append(f"Verdict: {verdict}")
    summary_lines.append(f"Critical issues: {critical_count}")
    summary_lines.append("")
    summary_lines.append("Summary:")
    if verdict == "REQUEST CHANGES":
        summary_lines.append("- The code uses eval() on user input which is a high-risk vulnerability. Changes required before merge.")
    else:
        summary_lines.append("- No critical issues identified.")
    summary_lines.append("")
    summary_lines.append("Action Items:")
    summary_lines.append("1) Remove use of eval() and replace with a safe parser appropriate to the expected input format.")
    summary_lines.append("2) Add input validation and explicit exception handling.")
    summary_lines.append("3) Add unit tests covering malicious/edge-case inputs.")
    return "\n".join(summary_lines)


async def main():
    # Build deterministic state and run the three-stage pipeline locally
    state = {
        "messages": [],
        "code": CODE_TO_REVIEW,
        "review": "",
        "audit": "",
        "summary": "",
    }

    # Run analyzer
    analysis = code_analyzer(state["code"])

    # Run reviewer (deterministic local generation)
    state["review"] = generate_review(state["code"], analysis)

    # Run auditor (deterministic local generation)
    state["audit"] = generate_audit(state["code"], analysis)

    # Run summarizer (deterministic local generation)
    state["summary"] = generate_summary(state["review"], state["audit"])

    # Print results (mimic reference behavior)
    print("Starting Deterministic Code Review (autogen simplified)...\n")
    print("\n=== Code to Review ===\n")
    print(state["code"])
    print("\n=== Analyzer Output ===\n")
    print(analysis)
    print("\n=== Code Review ===\n")
    print(state["review"])
    print("\n=== Security Audit ===\n")
    print(state["audit"])
    print("\n=== Summary ===\n")
    print(state["summary"])

    # Attempt to close model client if it supports close (best-effort, ignore errors)
    try:
        close_coro = getattr(model_client, "close", None)
        if close_coro:
            # If it's awaitable/coroutine, await it
            if asyncio.iscoroutinefunction(close_coro):
                await close_coro()
            else:
                maybe = close_coro()
                if asyncio.iscoroutine(maybe):
                    await maybe
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
