"""
Auto-generated CrewAI crew: ContentPipelineCrew
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from tools.WebSearchTool import WebSearchTool
from tools.WordCountTool import WordCountTool


@CrewBase
class ContentPipelineCrew:
    """ContentPipelineCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")


    @agent
    def content_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["content_writer"],
            tools=[WordCountTool()],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def quality_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["quality_reviewer"],
            tools=[WordCountTool()],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def research_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["research_analyst"],
            tools=[WebSearchTool()],
            llm=self.llm,
            verbose=True,
        )


    @task
    def research_topic(self) -> Task:
        return Task(
            config=self.tasks_config["research_topic"],
        )

    @task
    def write_article(self) -> Task:
        return Task(
            config=self.tasks_config["write_article"],
        )

    @task
    def review_content(self) -> Task:
        return Task(
            config=self.tasks_config["review_content"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ContentPipelineCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
