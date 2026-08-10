"""
Auto-generated CrewAI crew: StateGraph
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()


@CrewBase
class StateGraph:
    """StateGraph"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def generate_joke(self) -> Agent:
        return Agent(
            config=self.agents_config["generate_joke"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def improve_joke(self) -> Agent:
        return Agent(
            config=self.agents_config["improve_joke"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def polish_joke(self) -> Agent:
        return Agent(
            config=self.agents_config["polish_joke"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
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
