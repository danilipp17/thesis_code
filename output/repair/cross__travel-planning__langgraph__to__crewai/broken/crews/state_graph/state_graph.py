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
    def planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["planner_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def local_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["local_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def language_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["language_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def travel_summary_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["travel_summary_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )


    @task
    def task_planner_agent(self) -> Task:
        return Task(
            config=self.tasks_config["task_planner_agent"],
        )

    @task
    def task_local_agent(self) -> Task:
        return Task(
            config=self.tasks_config["task_local_agent"],
            context=[self.task_planner_agent()],
        )

    @task
    def task_language_agent(self) -> Task:
        return Task(
            config=self.tasks_config["task_language_agent"],
            context=[self.task_local_agent()],
        )

    @task
    def task_travel_summary_agent(self) -> Task:
        return Task(
            config=self.tasks_config["task_travel_summary_agent"],
            context=[self.task_language_agent()],
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
