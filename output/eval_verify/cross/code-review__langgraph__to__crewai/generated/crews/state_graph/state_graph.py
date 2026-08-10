"""
Auto-generated CrewAI crew: StateGraph
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()


@CrewBase
class StateGraph:
    """StateGraph"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["code_reviewer"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def security_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["security_auditor"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def review_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["review_summarizer"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )


    @task
    def task_code_reviewer(self) -> Task:
        return Task(
            config=self.tasks_config["task_code_reviewer"],
        )

    @task
    def task_security_auditor(self) -> Task:
        return Task(
            config=self.tasks_config["task_security_auditor"],
            context=[self.task_code_reviewer()],
        )

    @task
    def task_review_summarizer(self) -> Task:
        return Task(
            config=self.tasks_config["task_review_summarizer"],
            context=[self.task_security_auditor()],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the StateGraph"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
