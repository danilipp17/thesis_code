"""
Auto-generated CrewAI crew: editorial_team
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.web_search import web_search


@CrewBase
class editorial_team:
    """editorial_team"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            tools=[web_search()],
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
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config["research_task"],
        )

    @task
    def write_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_task"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the editorial_team"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
