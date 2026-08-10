"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.code_analyzer import code_analyzer

import yaml
from pathlib import Path


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    # load YAML configs at runtime (so config references work as expected)
    _base_path = Path(__file__).resolve().parent
    agents_config_path = _base_path / "config" / "agents.yaml"
    tasks_config_path = _base_path / "config" / "tasks.yaml"

    def __init__(self):
        # load YAML files into dictionaries
        try:
            with open(self.agents_config_path, "r", encoding="utf-8") as f:
                self.agents_config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self.agents_config = {}

        try:
            with open(self.tasks_config_path, "r", encoding="utf-8") as f:
                self.tasks_config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self.tasks_config = {}

    @agent
    def code_reviewer(self) -> Agent:
        # The Agent constructor expects a dict config; provide parsed YAML entry.
        cfg = self.agents_config.get("Code_Reviewer", {})
        return Agent(
            config=cfg,
            tools=[code_analyzer()],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def security_auditor(self) -> Agent:
        cfg = self.agents_config.get("Security_Auditor", {})
        return Agent(
            config=cfg,
            tools=[code_analyzer()],
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def review_summarizer(self) -> Agent:
        cfg = self.agents_config.get("Review_Summarizer", {})
        return Agent(
            config=cfg,
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
