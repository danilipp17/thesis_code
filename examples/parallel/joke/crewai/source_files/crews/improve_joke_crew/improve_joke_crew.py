from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class ImproveJokeCrew:
    """Single-agent crew that improves a joke by adding wordplay."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def joke_improver(self) -> Agent:
        return Agent(
            config=self.agents_config["joke_improver"],
            llm=self.llm,
            verbose=True,
        )

    @task
    def improve_joke_task(self) -> Task:
        return Task(config=self.tasks_config["improve_joke"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
