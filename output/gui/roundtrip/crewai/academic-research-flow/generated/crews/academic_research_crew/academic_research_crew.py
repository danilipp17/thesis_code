"""
Auto-generated CrewAI crew: AcademicResearchCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.AcademicSearchTool import AcademicSearchTool
from models import FinalPaper, ResearchOutline


@CrewBase
class AcademicResearchCrew:
    """AcademicResearchCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def manager_AcademicResearchCrew(self) -> Agent:
        return Agent(
            config=self.agents_config["manager_AcademicResearchCrew"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def prof_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["prof_writer"],
            llm="gpt-4o",
            verbose=False,
            allow_delegation=False,
            reasoning=False,
            memory=False,
        )

    @agent
    def senior_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_researcher"],
            tools=[AcademicSearchTool()],
            llm="gpt-4o",
            verbose=True,
            allow_delegation=True,
            reasoning=True,
            max_reasoning_attempts=3,
            memory=True,
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
