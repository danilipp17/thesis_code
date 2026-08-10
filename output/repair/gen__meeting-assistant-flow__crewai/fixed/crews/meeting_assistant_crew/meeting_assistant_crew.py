"""
Auto-generated CrewAI crew: MeetingAssistantCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from models import MeetingTaskList
from langchain_openai import ChatOpenAI


@CrewBase
class MeetingAssistantCrew:
    """MeetingAssistantCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # Use a real LLM instance so the agents perform model calls at runtime.
    llm = ChatOpenAI(model="gpt-4")

    @agent
    def meeting_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["meeting_analyzer"],
            llm=self.llm,
        )

    @task
    def analyze_meeting(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_meeting"],
            output_pydantic=MeetingTaskList,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MeetingAssistantCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
