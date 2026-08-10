"""
Auto-generated CrewAI crew: GenerateJokeCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()


@CrewBase
class GenerateJokeCrew:
    """GenerateJokeCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def joke_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["joke_generator"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )


    @task
    def generate_joke_task(self) -> Task:
        return Task(
            config=self.tasks_config["generate_joke_task"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the GenerateJokeCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
