from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from tools.arithmetic import add, multiply, subtract


@CrewBase
class MathsCrew:
    """Single-agent ReAct-style crew over arithmetic tools."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def our_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["our_agent"],
            tools=[add, subtract, multiply],
            llm=self.llm,
            verbose=True,
        )

    @task
    def answer_query(self) -> Task:
        return Task(config=self.tasks_config["answer_query"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
