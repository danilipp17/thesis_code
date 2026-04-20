"""
Auto-generated CrewAI crew: XPostReviewCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.CharacterCounterTool import CharacterCounterTool
from models import XPostVerification


@CrewBase
class XPostReviewCrew:
    """XPostReviewCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def x_post_verifier(self) -> Agent:
        return Agent(
            config=self.agents_config["x_post_verifier"],
            tools=[CharacterCounterTool()],
            reasoning=False,
            memory=False,
        )


    @task
    def verify_x_post(self) -> Task:
        return Task(
            config=self.tasks_config["verify_x_post"],
            output_pydantic=XPostVerification,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the XPostReviewCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
