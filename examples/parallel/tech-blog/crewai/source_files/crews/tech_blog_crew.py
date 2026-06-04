from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class TechBlogCrew:
    """Tech Blog Writing Crew — researcher → writer → editor."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm=self.llm,
            verbose=True,
        )

    @task
    def research_topic(self) -> Task:
        return Task(config=self.tasks_config["research_topic"])

    @task
    def write_draft(self) -> Task:
        return Task(config=self.tasks_config["write_draft"])

    @task
    def edit_post(self) -> Task:
        return Task(config=self.tasks_config["edit_post"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
