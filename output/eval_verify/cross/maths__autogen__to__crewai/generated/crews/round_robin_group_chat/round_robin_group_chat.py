"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.add import add
from tools.multiply import multiply
from tools.subtract import subtract


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def our_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["our_agent"],
            tools=[add(), subtract(), multiply()],
            llm="gpt-4o",
            reasoning=True,
            memory=False,
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
