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

    # Load YAML configs from the package config directory so agent() can access dicts
    # (original generation left these as raw strings which breaks config access).
    try:
        from pathlib import Path
        import yaml

        _base_dir = Path(__file__).parent / "config"
        _agents_path = _base_dir / "agents.yaml"
        _tasks_path = _base_dir / "tasks.yaml"

        if _agents_path.exists():
            with open(_agents_path, "r", encoding="utf-8") as f:
                agents_config = yaml.safe_load(f) or {}
        else:
            agents_config = {}

        if _tasks_path.exists():
            with open(_tasks_path, "r", encoding="utf-8") as f:
                tasks_config = yaml.safe_load(f) or {}
        else:
            tasks_config = {}
    except Exception:
        # Fall back to empty dicts if yaml/pathlib aren't available for some reason.
        agents_config = {}
        tasks_config = {}


    @agent
    def planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config.get("planner_agent", {}),
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def local_agent(self) -> Agent:
        return Agent(
            config=self.agents_config.get("local_agent", {}),
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def language_agent(self) -> Agent:
        return Agent(
            config=self.agents_config.get("language_agent", {}),
            llm="gpt-4o",
            reasoning=False,
            memory=False,
        )

    @agent
    def travel_summary_agent(self) -> Agent:
        return Agent(
            config=self.agents_config.get("travel_summary_agent", {}),
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
