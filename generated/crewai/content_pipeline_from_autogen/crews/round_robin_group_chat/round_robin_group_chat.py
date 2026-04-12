"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from tools.web_search_tool import web_search_tool
from tools.word_count_tool import word_count_tool


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")


    @agent
    def Content_Writer(self) -> Agent:
        return Agent(
            config=self.agents_config["Content_Writer"],
            tools=[word_count_tool()],
            llm=self.llm,
        )

    @agent
    def Quality_Reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["Quality_Reviewer"],
            tools=[word_count_tool()],
            llm=self.llm,
        )

    @agent
    def Research_Analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["Research_Analyst"],
            tools=[web_search_tool()],
            llm=self.llm,
        )


    @crew
    def crew(self) -> Crew:
        """Creates the RoundRobinGroupChat"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
