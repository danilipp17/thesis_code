from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class TravelPlanningCrew:
    """Four-agent crew: planner, local guide, language adviser, summary."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    llm = "gpt-4o"

    @agent
    def planner_agent(self) -> Agent:
        return Agent(config=self.agents_config["planner_agent"], llm=self.llm, verbose=True)

    @agent
    def local_agent(self) -> Agent:
        return Agent(config=self.agents_config["local_agent"], llm=self.llm, verbose=True)

    @agent
    def language_agent(self) -> Agent:
        return Agent(config=self.agents_config["language_agent"], llm=self.llm, verbose=True)

    @agent
    def travel_summary_agent(self) -> Agent:
        return Agent(config=self.agents_config["travel_summary_agent"], llm=self.llm, verbose=True)

    @task
    def planning_task(self) -> Task:
        return Task(config=self.tasks_config["planning_task"])

    @task
    def local_task(self) -> Task:
        return Task(config=self.tasks_config["local_task"])

    @task
    def language_task(self) -> Task:
        return Task(config=self.tasks_config["language_task"])

    @task
    def summary_task(self) -> Task:
        return Task(config=self.tasks_config["summary_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
