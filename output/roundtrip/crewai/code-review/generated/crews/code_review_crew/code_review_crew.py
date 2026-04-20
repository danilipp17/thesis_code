"""
Auto-generated CrewAI crew: CodeReviewCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.CodeAnalyzerTool import CodeAnalyzerTool
from models import ReviewResult


@CrewBase
class CodeReviewCrew:
    """CodeReviewCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],
            tools=[CodeAnalyzerTool()],
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

    @agent
    def security_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["security_auditor"],
            tools=[CodeAnalyzerTool()],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )


    @task
    def review_code(self) -> Task:
        return Task(
            config=self.tasks_config["review_code"],
        )

    @task
    def audit_security(self) -> Task:
        return Task(
            config=self.tasks_config["audit_security"],
        )

    @task
    def compile_review(self) -> Task:
        return Task(
            config=self.tasks_config["compile_review"],
            output_pydantic=ReviewResult,
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
