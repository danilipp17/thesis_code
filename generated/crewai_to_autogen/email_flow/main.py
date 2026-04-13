"""
Auto-generated AutoGen application: EmailFlow
"""

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.tools import FunctionTool

from tools import serper_dev_tool, create_draft, gmail_get_thread, tavily_search_results

model_client = OpenAIChatCompletionClient(model="gpt-4o")

# -- Tools --
serper_dev_tool_tool = FunctionTool(
    serper_dev_tool,
    description="",
)
create_draft_tool = FunctionTool(
    create_draft,
    description="Useful to create an email draft. The input to this tool should be a pipe (|) separated text of length 3 (three), representing who to send the email to, the subject of the email and the actual message. For example, `lorem@ipsum.com|Nice To Meet You|Hey it was great to meet you.`.",
)
gmail_get_thread_tool = FunctionTool(
    gmail_get_thread,
    description="",
)
tavily_search_results_tool = FunctionTool(
    tavily_search_results,
    description="",
)

# -- Agents --
email_action_agent = AssistantAgent(
    name="Email Action Specialist",
    model_client=model_client,
    tools=[gmail_get_thread_tool, tavily_search_results_tool],
    system_message=(
        "For each email identified as action-required, determine the necessary steps and provide a brief summary of the required actions. As a seasoned executive assistant, you excel at understanding the context of business communications and determining the appropriate response and actions required for each email."
    ),
)

email_filter_agent = AssistantAgent(
    name="Senior Email Analyst",
    model_client=model_client,
    tools=[serper_dev_tool_tool],
    system_message=(
        "Filter out non-essential emails like newsletters and promotional content, and identify important action-required emails that need immediate attention. With years of experience in email management and communication triage, you are adept at quickly identifying important emails that require immediate action from those that can be archived or ignored."
    ),
)

email_response_writer = AssistantAgent(
    name="Email Response Writer",
    model_client=model_client,
    tools=[gmail_get_thread_tool, tavily_search_results_tool, create_draft_tool],
    system_message=(
        "Draft professional and appropriate responses to action-required emails based on the determined actions and context. You are a skilled communicator with a talent for crafting clear, professional, and context-appropriate email responses. You understand the nuances of business communication and can adapt your tone and style to match the situation."
    ),
)

# -- Team --
team = RoundRobinGroupChat(
    participants=[email_action_agent, email_filter_agent, email_response_writer],
)


async def main():
    stream = team.run_stream(
        task="Start the task."  # TODO: provide initial message
    )
    await Console(stream)
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
