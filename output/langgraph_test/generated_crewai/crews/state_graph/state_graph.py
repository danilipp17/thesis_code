"""
Auto-generated CrewAI crew: StateGraph
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from tools.save_notes import save_notes
from tools.search_web import search_web


@CrewBase
class StateGraph:
    """StateGraph"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = ChatOpenAI(model="gpt-4o")


    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            tools=[save_notes(), search_web()],
            llm=self.llm,
            reasoning=False,
            memory=False,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            llm=self.llm,
            reasoning=False,
            memory=False,
        )


    @task
    def task_researcher(self) -> Task:
        return Task(
            config=self.tasks_config["task_researcher"],
        )

    @task
    def task_writer(self) -> Task:
        return Task(
            config=self.tasks_config["task_writer"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the StateGraph"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            verbose=False,
        )
