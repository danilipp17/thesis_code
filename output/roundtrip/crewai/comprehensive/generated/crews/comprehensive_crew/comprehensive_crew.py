"""
Auto-generated CrewAI crew: ComprehensiveCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.DatabaseTool import DatabaseTool
from tools.web_search import web_search
from models import AnalysisOutput


@CrewBase
class ComprehensiveCrew:
    """ComprehensiveCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def primary_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["primary_researcher"],
            tools=[web_search()],
            llm="gpt-4-turbo",
            verbose=True,
            reasoning=False,
            memory=True,
        )

    @agent
    def senior_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_analyst"],
            tools=[DatabaseTool()],
            llm="gpt-4-turbo",
            allow_delegation=False,
            reasoning=False,
            memory=False,
        )


    @task
    def data_gathering(self) -> Task:
        return Task(
            config=self.tasks_config["data_gathering"],
        )

    @task
    def analysis_phase(self) -> Task:
        return Task(
            config=self.tasks_config["analysis_phase"],
            output_pydantic=AnalysisOutput,
            human_input=True,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ComprehensiveCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            verbose=True,
        )
