"""
Auto-generated CrewAI crew: AcademicResearchCrew
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from tools.AcademicSearchTool import AcademicSearchTool
from models import FinalPaper, ResearchOutline


@CrewBase
class AcademicResearchCrew:
    """AcademicResearchCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")


    @agent
    def prof_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["prof_writer"],
            llm=self.llm,
            verbose=False,
            allow_delegation=False,
        )

    @agent
    def senior_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_researcher"],
            tools=[AcademicSearchTool()],
            llm=self.llm,
            verbose=True,
            allow_delegation=True,
        )


    @task
    def gather_literature_task(self) -> Task:
        return Task(
            config=self.tasks_config["gather_literature_task"],
            output_pydantic=ResearchOutline,
            human_input=True,
        )

    @task
    def write_paper_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_paper_task"],
            output_pydantic=FinalPaper,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AcademicResearchCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            verbose=True,
        )
