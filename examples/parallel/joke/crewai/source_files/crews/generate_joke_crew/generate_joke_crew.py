from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class GenerateJokeCrew:
    """Single-agent crew that writes a short joke on the given topic."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def joke_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["joke_generator"],
            llm=self.llm,
            verbose=True,
        )

    @task
    def generate_joke_task(self) -> Task:
        return Task(config=self.tasks_config["generate_joke"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
