from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI

from pydantic import BaseModel
from typing import List


class CandidateSummary(BaseModel):
    name: str
    matched_skills: List[str]
    experience_years: int
    screening_score: float


@CrewBase
class HiringCrew:
    """Hiring Pipeline Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")

    @agent
    def resume_screener(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_screener"],
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    @agent
    def technical_interviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["technical_interviewer"],
            llm=self.llm,
            verbose=True,
            memory=True,
        )

    @agent
    def hiring_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["hiring_manager"],
            llm=self.llm,
            verbose=True,
            allow_delegation=True,
        )

    @task
    def screen_resume(self) -> Task:
        return Task(
            config=self.tasks_config["screen_resume"],
            output_pydantic=CandidateSummary,
        )

    @task
    def conduct_technical_interview(self) -> Task:
        return Task(
            config=self.tasks_config["conduct_technical_interview"],
            context=[self.screen_resume()],
            human_input=True,
        )

    @task
    def make_hiring_decision(self) -> Task:
        return Task(
            config=self.tasks_config["make_hiring_decision"],
            context=[self.screen_resume(), self.conduct_technical_interview()],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Hiring Pipeline Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
        )
