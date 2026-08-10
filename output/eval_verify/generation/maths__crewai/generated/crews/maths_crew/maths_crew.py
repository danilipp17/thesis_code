"""
Auto-generated CrewAI crew: MathsCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.add import add
from tools.multiply import multiply
from tools.subtract import subtract


@CrewBase
class MathsCrew:
    """MathsCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def our_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["our_agent"],
            tools=[add(), subtract(), multiply()],
            llm="gpt-4o",
            verbose=True,
            reasoning=False,
            memory=False,
        )


    @task
    def answer_query(self) -> Task:
        return Task(
            config=self.tasks_config["answer_query"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MathsCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
