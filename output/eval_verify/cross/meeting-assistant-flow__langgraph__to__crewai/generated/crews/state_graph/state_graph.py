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
    def analyze_meeting(self) -> Agent:
        return Agent(
            config=self.agents_config["analyze_meeting"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )


    @task
    def task_analyze_meeting(self) -> Task:
        return Task(
            config=self.tasks_config["task_analyze_meeting"],
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
