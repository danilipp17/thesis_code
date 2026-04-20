"""
Auto-generated CrewAI crew: TechBlogCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()


@CrewBase
class TechBlogCrew:
    """TechBlogCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )


    @task
    def research_topic(self) -> Task:
        return Task(
            config=self.tasks_config["research_topic"],
        )

    @task
    def write_draft(self) -> Task:
        return Task(
            config=self.tasks_config["write_draft"],
            context=[self.research_topic()],
        )

    @task
    def edit_post(self) -> Task:
        return Task(
            config=self.tasks_config["edit_post"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the TechBlogCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
