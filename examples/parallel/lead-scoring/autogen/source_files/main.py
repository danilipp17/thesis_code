"""
lead-scoring — AutoGen v0.4 port of the CrewAI original.

Original: examples/parallel/lead-scoring/crewai — a CrewAI Flow over two
sub-crews (LeadScoreCrew / hr_evaluation_agent and LeadResponseCrew /
email_followup_agent) with a @router human-in-the-loop gate.

AutoGen mapping:
  - LeadScoreCrew agent    -> hr_evaluation_agent (AssistantAgent, scores leads).
  - LeadResponseCrew agent -> email_followup_agent (AssistantAgent, writes emails).
  - @router human review   -> a UserProxyAgent (human_reviewer) interleaved in a
    RoundRobinGroupChat so a human can review between scoring and emailing.
"""

from dotenv import load_dotenv

load_dotenv()

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o")

hr_evaluation_agent = AssistantAgent(
    name="hr_evaluation_agent",
    model_client=model_client,
    description="Scores candidates against the job description.",
    system_message=(
        "You are a Senior HR Evaluation Expert. Analyze candidates' qualifications "
        "and compare them against the job description to provide a score (1-100) "
        "and detailed reasoning, considering skill match, experience, cultural fit, "
        "and growth potential."
    ),
)

email_followup_agent = AssistantAgent(
    name="email_followup_agent",
    model_client=model_client,
    description="Writes personalized follow-up emails to candidates.",
    system_message=(
        "You are an HR Coordinator named Sarah. Compose personalized follow-up "
        "emails to candidates based on their bio and whether they are being "
        "pursued. If proceeding, request availability for a Zoom call; otherwise "
        "send a polite rejection email. When finished, reply with TERMINATE."
    ),
)

human_reviewer = UserProxyAgent(
    name="human_reviewer",
    description="A human who reviews the scored leads before emails are written.",
)

team = RoundRobinGroupChat(
    [hr_evaluation_agent, human_reviewer, email_followup_agent],
    max_turns=3,
)


async def main():
    await Console(
        team.run_stream(
            task=(
                "Score the candidates in leads.csv against the Junior React "
                "Developer role, let the human review, then write follow-up emails."
            )
        )
    )
    await model_client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
