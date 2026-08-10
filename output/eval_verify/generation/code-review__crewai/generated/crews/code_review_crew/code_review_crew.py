"""
Auto-generated CrewAI crew: CodeReviewCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.code_analyzer import code_analyzer


@CrewBase
class CodeReviewCrew:
    """CodeReviewCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],
            tools=[code_analyzer()],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def security_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["security_auditor"],
            tools=[code_analyzer()],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def review_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["review_summarizer"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )


    @task
    def code_review(self) -> Task:
        return Task(
            config=self.tasks_config["code_review"],
        )

    @task
    def security_audit(self) -> Task:
        return Task(
            config=self.tasks_config["security_audit"],
            context=[self.code_review()],
        )

    @task
    def summary(self) -> Task:
        return Task(
            config=self.tasks_config["summary"],
            context=[self.security_audit()],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the CodeReviewCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
