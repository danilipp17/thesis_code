"""
Auto-generated AutoGen application: EmailFlowSystem
"""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

from tools import serper_dev_tool, create_draft, gmail_get_thread, tavily_search_results

llm_config = {"model": "gpt-4o"}

email_action_agent = AssistantAgent(
    name="Email Action Specialist",
    system_message="""Role: Email Action Specialist
Goal: For each email identified as action-required, determine the necessary steps and provide a brief summary of the required actions.
As a seasoned executive assistant, you excel at understanding the context of business communications and determining the appropriate response and actions required for each email.""",
    llm_config=llm_config,
)

email_filter_agent = AssistantAgent(
    name="Senior Email Analyst",
    system_message="""Role: Senior Email Analyst
Goal: Filter out non-essential emails like newsletters and promotional content, and identify important action-required emails that need immediate attention.
With years of experience in email management and communication triage, you are adept at quickly identifying important emails that require immediate action from those that can be archived or ignored.""",
    llm_config=llm_config,
)

email_response_writer = AssistantAgent(
    name="Email Response Writer",
    system_message="""Role: Email Response Writer
Goal: Draft professional and appropriate responses to action-required emails based on the determined actions and context.
You are a skilled communicator with a talent for crafting clear, professional, and context-appropriate email responses. You understand the nuances of business communication and can adapt your tone and style to match the situation.""",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

groupchat_email_filter_crew = GroupChat(
    agents=[user_proxy, email_action_agent, email_filter_agent, email_response_writer],
    messages=[],
    max_round=10,
)

manager_email_filter_crew = GroupChatManager(
    groupchat=groupchat_email_filter_crew,
    llm_config=llm_config,
)

# Register tools
email_filter_agent.register_for_llm(
    name="serper_dev_tool",
    description="",
)(serper_dev_tool)
user_proxy.register_for_execution()(serper_dev_tool)

email_response_writer.register_for_llm(
    name="create_draft",
    description="Useful to create an email draft. The input to this tool should be a pipe (|) separated text of length 3 (three), representing who to send the email to, the subject of the email and the actual message. For example, `lorem@ipsum.com|Nice To Meet You|Hey it was great to meet you.`.",
)(create_draft)
user_proxy.register_for_execution()(create_draft)

email_action_agent.register_for_llm(
    name="gmail_get_thread",
    description="",
)(gmail_get_thread)
email_response_writer.register_for_llm(
    name="gmail_get_thread",
    description="",
)(gmail_get_thread)
user_proxy.register_for_execution()(gmail_get_thread)

email_action_agent.register_for_llm(
    name="tavily_search_results",
    description="",
)(tavily_search_results)
email_response_writer.register_for_llm(
    name="tavily_search_results",
    description="",
)(tavily_search_results)
user_proxy.register_for_execution()(tavily_search_results)


if __name__ == "__main__":
    user_proxy.initiate_chat(
        manager_email_filter_crew,
        message="Start the task.",  # TODO: provide initial message
    )
