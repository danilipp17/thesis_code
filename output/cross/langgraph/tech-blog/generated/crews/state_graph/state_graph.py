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
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )


    @task
    def task_researcher(self) -> Task:
        return Task(
            config=self.tasks_config["task_researcher"],
        )

    @task
    def task_writer(self) -> Task:
        return Task(
            config=self.tasks_config["task_writer"],
            context=[self.task_researcher()],
        )

    @task
    def task_editor(self) -> Task:
        return Task(
            config=self.tasks_config["task_editor"],
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
