from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class PolishJokeCrew:
    """Single-agent crew that adds a surprising twist to the improved joke."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def joke_polisher(self) -> Agent:
        return Agent(
            config=self.agents_config["joke_polisher"],
            llm=self.llm,
            verbose=True,
        )

    @task
    def polish_joke_task(self) -> Task:
        return Task(config=self.tasks_config["polish_joke"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
