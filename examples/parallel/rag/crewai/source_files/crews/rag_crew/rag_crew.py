from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from tools.retriever import retriever_tool


@CrewBase
class RagCrew:
    """Single-agent RAG crew over the Stock Market 2024 document."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def rag_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["rag_agent"],
            tools=[retriever_tool],
            llm=self.llm,
            verbose=True,
        )

    @task
    def answer_question(self) -> Task:
        return Task(config=self.tasks_config["answer_question"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
