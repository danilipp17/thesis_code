"""
Auto-generated CrewAI crew: CodeReviewCrew
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from tools.CodeAnalyzerTool import CodeAnalyzerTool
from models import ReviewResult


@CrewBase
class CodeReviewCrew:
    """CodeReviewCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")


    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],
            tools=[CodeAnalyzerTool()],
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

    @agent
    def security_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["security_auditor"],
            tools=[CodeAnalyzerTool()],
            llm=self.llm,
            verbose=True,
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
