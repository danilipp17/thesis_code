from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from models import ResearchOutline, FinalPaper
from tools.custom_tools import AcademicSearchTool

@CrewBase
class AcademicResearchCrew():
    """AcademicResearch crew"""

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    @agent
    def senior_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['senior_researcher'],
            tools=[AcademicSearchTool()],
            llm="gpt-4o",
            allow_delegation=True,
            reasoning=True,
            max_reasoning_attempts=3,
            memory=True,
            verbose=True
        )

    @agent
    def prof_writer(self) -> Agent:
        return Agent(
            config=self.agents_config['prof_writer'],
            llm="gpt-4o",
            allow_delegation=False,
            reasoning=False,
            memory=False,
            verbose=False
        )

    @task
    def gather_literature_task(self) -> Task:
        return Task(
            config=self.tasks_config['gather_literature_task'],
            agent=self.senior_researcher(),
            output_pydantic=ResearchOutline,
            human_input=True
        )

    @task
    def write_paper_task(self) -> Task:
        return Task(
            config=self.tasks_config['write_paper_task'],
            agent=self.prof_writer(),
            output_pydantic=FinalPaper,
            context=[self.gather_literature_task()]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_llm="gpt-4o",
            memory=True,
            verbose=True
        )
