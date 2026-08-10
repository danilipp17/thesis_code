"""
Auto-generated CrewAI crew: RoundRobinGroupChat
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.add import add
from tools.multiply import multiply
from tools.subtract import subtract


@CrewBase
class RoundRobinGroupChat:
    """RoundRobinGroupChat"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"


    @agent
    def our_agent(self) -> Agent:
        # Load the YAML config for the agent so we pass a real config dict
        # into the Agent constructor (the generator left a string path).
        # Import locally to avoid changing top-level imports.
        import os
        import yaml

        cfg_path = os.path.join(os.path.dirname(__file__), "config", "agents.yaml")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except FileNotFoundError:
            cfg = {}

        # The generated config uses a mapping with key "our_agent"
        agent_cfg = cfg.get("our_agent", {})

        # Instantiate and return an Agent instance with concrete tool objects.
        return Agent(
            config=agent_cfg,
            tools=[add(), subtract(), multiply()],
            llm="gpt-4o",
            reasoning=True,
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
