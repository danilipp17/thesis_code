from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from tools.code_analyzer import code_analyzer


@CrewBase
class CodeReviewCrew:
    """Three-agent crew: reviewer, security auditor, and summarizer."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],
            tools=[code_analyzer],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def security_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["security_auditor"],
            tools=[code_analyzer],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def review_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["review_summarizer"],
            llm=self.llm,
            verbose=True,
        )

    @task
    def code_review(self) -> Task:
        return Task(config=self.tasks_config["code_review"])

    @task
    def security_audit(self) -> Task:
        return Task(config=self.tasks_config["security_audit"])

    @task
    def summary(self) -> Task:
        return Task(config=self.tasks_config["summary"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
