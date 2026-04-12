"""
Auto-generated AutoGen application: CodeReviewSystem
"""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

from tools import code_analyzer_tool

llm_config = {"model": "gpt-4o"}

code_reviewer = AssistantAgent(
    name="Senior Code Reviewer",
    system_message="""Role: Senior Code Reviewer
Goal: Perform a thorough code review, checking for correctness, readability, and adherence to best practices. Identify bugs, code smells, and potential improvements.
You are a senior software engineer with 15 years of experience in code review. You have reviewed thousands of pull requests across multiple languages and frameworks, giving you a sharp eye for common pitfalls and anti-patterns.""",
    llm_config=llm_config,
)

review_summarizer = AssistantAgent(
    name="Review Summarizer",
    system_message="""Role: Review Summarizer
Goal: Compile code review and security audit findings into a structured review report with an overall verdict (approve or request changes).
You are a technical lead who synthesizes feedback from multiple reviewers into clear, actionable review summaries. You balance thoroughness with pragmatism, distinguishing blockers from nits.""",
    llm_config=llm_config,
)

security_auditor = AssistantAgent(
    name="Security Auditor",
    system_message="""Role: Security Auditor
Goal: Audit code for security vulnerabilities including injection attacks, authentication flaws, data exposure, and insecure dependencies. Flag any OWASP Top 10 violations.
You are a certified security professional specializing in application security. You have experience in penetration testing and secure code review, and you stay current with the latest CVEs and vulnerability disclosures.""",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

groupchat_code_review_crew = GroupChat(
    agents=[user_proxy, code_reviewer, review_summarizer, security_auditor],
    messages=[],
    max_round=10,
)

manager_code_review_crew = GroupChatManager(
    groupchat=groupchat_code_review_crew,
    llm_config=llm_config,
)

# Register tools
code_reviewer.register_for_llm(
    name="code_analyzer_tool",
    description="Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.",
)(code_analyzer_tool)
security_auditor.register_for_llm(
    name="code_analyzer_tool",
    description="Performs static analysis on source code. Checks for syntax errors, undefined variables, unused imports, and common anti-patterns.",
)(code_analyzer_tool)
user_proxy.register_for_execution()(code_analyzer_tool)


if __name__ == "__main__":
    user_proxy.initiate_chat(
        manager_code_review_crew,
        message="Start the task.",  # TODO: provide initial message
    )
