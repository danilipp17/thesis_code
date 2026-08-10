"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Added imports for YAML parsing
from pathlib import Path
import yaml

dotenv.load_dotenv()


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    # keep the original config paths, we'll parse them at runtime
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def meeting_analyzer(self) -> Agent:
        # Load the YAML agents config at runtime and extract the meeting_analyzer block.
        # The generated class originally set agents_config to a string path; the template
        # expected the decorator/framework to resolve it. Here we resolve manually.
        agents_path = Path(__file__).parent / self.agents_config
        try:
            with open(agents_path, "r", encoding="utf-8") as f:
                parsed = yaml.safe_load(f) or {}
        except FileNotFoundError:
            parsed = {}

        meeting_cfg = parsed.get("meeting_analyzer", {})

        return Agent(
            config=meeting_cfg,
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
