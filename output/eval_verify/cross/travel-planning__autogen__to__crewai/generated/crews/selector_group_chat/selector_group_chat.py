"""
Auto-generated CrewAI crew: SelectorGroupChat
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()


@CrewBase
class SelectorGroupChat:
    """SelectorGroupChat"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["planner_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def local_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["local_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def language_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["language_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def travel_summary_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["travel_summary_agent"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )


    @crew
    def crew(self) -> Crew:
        """Creates the SelectorGroupChat"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
