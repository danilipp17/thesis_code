"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from tools.code_analyzer_tool import code_analyzer_tool


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")


    @agent
    def Code_Reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["Code_Reviewer"],
            tools=[code_analyzer_tool()],
            llm=self.llm,
        )

    @agent
    def Review_Summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["Review_Summarizer"],
            llm=self.llm,
        )

    @agent
    def Security_Auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["Security_Auditor"],
            tools=[code_analyzer_tool()],
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
