"""
Auto-generated CrewAI crew: MathsCrew
"""

import dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

dotenv.load_dotenv()
from tools.add import add
from tools.multiply import multiply
from tools.subtract import subtract

import yaml
from pathlib import Path


@CrewBase
class MathsCrew:
    """MathsCrew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def our_agent(self) -> Agent:
        # Load agent config from the YAML file in the config directory
        cfg_path = Path(__file__).parent / "config" / "agents.yaml"
        with open(cfg_path, "r", encoding="utf-8") as fh:
            agents_cfg = yaml.safe_load(fh)
        agent_cfg = agents_cfg.get("our_agent", {})

        return Agent(
            config=agent_cfg,
            tools=[add(), subtract(), multiply()],
            llm="gpt-4o",
            verbose=True,
        )

    @task
    def answer_query(self) -> Task:
        # Load task config from the YAML file in the config directory
        cfg_path = Path(__file__).parent / "config" / "tasks.yaml"
        with open(cfg_path, "r", encoding="utf-8") as fh:
            tasks_cfg = yaml.safe_load(fh)
        task_cfg = tasks_cfg.get("answer_query", {})

        return Task(
            config=task_cfg,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the MathsCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
