"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def joke_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["Joke_Generator"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def joke_improver(self) -> Agent:
        return Agent(
            config=self.agents_config["Joke_Improver"],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def joke_polisher(self) -> Agent:
        return Agent(
            config=self.agents_config["Joke_Polisher"],
            llm="gpt-4o",
            reasoning=False,
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
