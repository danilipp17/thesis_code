"""
Auto-generated CrewAI crew: EmailFilterCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from crewai_tools import SerperDevTool
from langchain_community.tools.gmail.get_thread import GmailGetThread
from langchain_community.tools.tavily_search import TavilySearchResults
from tools.create_draft import create_draft


@CrewBase
class EmailFilterCrew:
    """EmailFilterCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def email_action_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["email_action_agent"],
            tools=[GmailGetThread(), TavilySearchResults()],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def email_filter_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["email_filter_agent"],
            tools=[SerperDevTool()],
            llm="gpt-4o",
            verbose=True,
            allow_delegation=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def email_response_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["email_response_writer"],
            tools=[GmailGetThread(), TavilySearchResults(), create_draft()],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )


    @task
    def filter_emails_task(self) -> Task:
        return Task(
            config=self.tasks_config["filter_emails_task"],
        )

    @task
    def action_required_emails_task(self) -> Task:
        return Task(
            config=self.tasks_config["action_required_emails_task"],
        )

    @task
    def draft_responses_task(self) -> Task:
        return Task(
            config=self.tasks_config["draft_responses_task"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the EmailFilterCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
