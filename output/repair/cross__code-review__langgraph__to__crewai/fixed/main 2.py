"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()


CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""


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
        # Implement the reviewer logic: run static analysis and produce a review.
        state = getattr(self, "_state", None)
        if state is None:
            # nothing to do if kickoff didn't initialize state
            return

        # import tool locally to avoid changing top-level import structure
        from tools import code_analyzer

        analysis = code_analyzer(state.code)
        # Simple deterministic reviewer output that mirrors the LangGraph original intent.
        review_lines = [
            "Reviewer: Senior Software Engineer (simulated).",
            "Reviewed for correctness, readability, and best practices.",
            "",
            "Code:",
            state.code,
            "",
            "Analyzer output:",
            analysis,
            "",
            "Findings:",
        ]

        if "eval(" in state.code:
            review_lines.append("- Use of eval() on untrusted input is dangerous; consider safer parsing or validation.")
            review_lines.append("- Missing input validation for `data` parameter.")
            review_lines.append("- Potential code injection vulnerability.")
        else:
            review_lines.append("- No obvious correctness issues found.")
        review_lines.append("")
        review_lines.append("Suggestions:")
        review_lines.append("- Avoid eval; use ast.literal_eval or dedicated parsing.")
        review_lines.append("- Add explicit input validation and error handling.")
        review_text = "\n".join(review_lines)

        state.review = review_text

    @listen(code_reviewer)
    def security_auditor(self):
        # Implement the security auditor logic: run static analysis and produce an audit.
        state = getattr(self, "_state", None)
        if state is None:
            return

        from tools import code_analyzer

        analysis = code_analyzer(state.code)
        audit_lines = [
            "Security Auditor: Certified Application Security Professional (simulated).",
            "",
            "Code:",
            state.code,
            "",
            "Analyzer output:",
            analysis,
            "",
            "Security Findings:",
        ]

        critical_count = 0
        if "eval(" in state.code:
            audit_lines.append("- Critical: Use of eval() allows arbitrary code execution (CWE-94).")
            audit_lines.append("  Recommendation: Remove eval or strictly sanitize/parse input before evaluation.")
            critical_count += 1
        else:
            audit_lines.append("- No critical vulnerabilities detected by static checks.")

        audit_lines.append("")
        audit_lines.append("CWE classifications (simulated):")
        if critical_count:
            audit_lines.append("- CWE-94: Improper Control of Generation of Code ('Code Injection').")
            audit_lines.append("- CWE-20: Improper Input Validation.")
        else:
            audit_lines.append("- None identified.")

        state.audit = "\n".join(audit_lines)

    @listen(security_auditor)
    def review_summarizer(self):
        # Synthesize review and audit into a summary and print final results.
        state = getattr(self, "_state", None)
        if state is None:
            return

        # Very small heuristic to decide verdict
        verdict = "APPROVED"
        criticals = 0
        if "CWE-94" in state.audit or "Critical" in state.audit or "eval(" in state.code:
            verdict = "REQUEST CHANGES"
            criticals = 1

        summary_lines = [
            "Summary (simulated technical lead):",
            f"Verdict: {verdict}",
            "",
            "Summary of findings:",
            state.review,
            "",
            state.audit,
            "",
            f"Critical count: {criticals}",
            "",
            "Action items:",
        ]

        if verdict == "REQUEST CHANGES":
            summary_lines.append("- Remove use of eval() and implement safe parsing.")
            summary_lines.append("- Add input validation and unit tests for edge cases.")
            summary_lines.append("- Perform security review after changes.")
        else:
            summary_lines.append("- No action required.")

        state.summary = "\n".join(summary_lines)

        # Print the outputs to match the original program behavior
        print("Starting CrewAI Code Review (simulated)...\n")
        print("=== Code Review ===\n")
        print(state.review)
        print("\n=== Security Audit ===\n")
        print(state.audit)
        print("\n=== Summary ===\n")
        print(state.summary)


def kickoff():
    flow = StateGraph()
    # Initialize state with representative concrete input
    flow._state = CodeReviewState(code=CODE_TO_REVIEW)
    # Run steps sequentially (decorators are preserved but we call methods directly)
    flow.code_reviewer()
    flow.security_auditor()
    flow.review_summarizer()


if __name__ == "__main__":
    kickoff()
