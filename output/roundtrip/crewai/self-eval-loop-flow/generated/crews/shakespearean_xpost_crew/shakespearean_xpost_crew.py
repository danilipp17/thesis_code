"""
Auto-generated CrewAI crew: ShakespeareanXPostCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.CharacterCounterTool import CharacterCounterTool


@CrewBase
class ShakespeareanXPostCrew:
    """ShakespeareanXPostCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def shakespearean_bard(self) -> Agent:
        return Agent(
            config=self.agents_config["shakespearean_bard"],
            tools=[CharacterCounterTool()],
            reasoning=False,
            memory=False,
        )


    @task
    def write_x_post(self) -> Task:
        return Task(
            config=self.tasks_config["write_x_post"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ShakespeareanXPostCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
