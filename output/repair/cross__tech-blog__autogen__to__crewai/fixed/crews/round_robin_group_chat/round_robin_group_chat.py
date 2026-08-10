"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

import os
import yaml
import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()

# Load YAML configs once at module import so agent factory methods can index into them.
_config_dir = os.path.join(os.path.dirname(__file__), "config")
_agents_path = os.path.join(_config_dir, "agents.yaml")
_tasks_path = os.path.join(_config_dir, "tasks.yaml")

# Safe defaults if files missing
_agents_config_data = {}
_tasks_config_data = {}

try:
    with open(_agents_path, "r", encoding="utf-8") as f:
        _agents_config_data = yaml.safe_load(f) or {}
except FileNotFoundError:
    _agents_config_data = {}

try:
    with open(_tasks_path, "r", encoding="utf-8") as f:
        _tasks_config_data = yaml.safe_load(f) or {}
except FileNotFoundError:
    _tasks_config_data = {}


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    # Provide parsed config dicts to the CrewBase-backed class
    agents_config = _agents_config_data
    tasks_config = _tasks_config_data

    @agent
    def researcher(self) -> Agent:
        # Build an Agent using the loaded YAML entry for Researcher.
        # The Agent constructor in CrewAI accepts a config mapping for persona details.
        return Agent(
            config=self.agents_config.get("Researcher", {}),
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config.get("Writer", {}),
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config.get("Editor", {}),
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the RoundRobinGroupChat"""
        # The Crew constructor is expected to take the resolved agents and tasks that
        # CrewBase wiring supplies on the instance (self.agents, self.tasks).
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
