"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.code_analyzer import code_analyzer


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def code_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["Code_Reviewer"],
            tools=[code_analyzer()],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def security_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["Security_Auditor"],
            tools=[code_analyzer()],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def review_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["Review_Summarizer"],
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
