"""
Auto-generated CrewAI crew: TravelPlanningCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()


@CrewBase
class TravelPlanningCrew:
    """TravelPlanningCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["planner_agent"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def local_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["local_agent"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def language_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["language_agent"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def travel_summary_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["travel_summary_agent"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )


    @task
    def planning_task(self) -> Task:
        return Task(
            config=self.tasks_config["planning_task"],
        )

    @task
    def local_task(self) -> Task:
        return Task(
            config=self.tasks_config["local_task"],
            context=[self.planning_task()],
        )

    @task
    def language_task(self) -> Task:
        return Task(
            config=self.tasks_config["language_task"],
            context=[self.local_task()],
        )

    @task
    def summary_task(self) -> Task:
        return Task(
            config=self.tasks_config["summary_task"],
            context=[self.language_task()],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the TravelPlanningCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
