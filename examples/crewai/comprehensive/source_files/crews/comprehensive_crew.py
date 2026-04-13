from pydantic import BaseModel, Field
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from typing import List


# 1. Triggers 'agentoscin:Schema' via ExtractedPydanticModel
class AnalysisOutput(BaseModel):
    findings: List[str] = Field(description="Key insights derived from data.")
    confidence_score: float = Field(description="Score between 0.0 and 1.0")


# 2. Triggers 'agentoscin:Tool' (Class-based)
class DatabaseTool(BaseTool):
    name: str = "Database_Query"
    description: str = "Query the internal database."

    def _run(self, query: str) -> str:
        return "Database response"


# 3. Triggers 'agentoscin:Tool' (Function-based)
@tool("Web_Search")
def web_search(query: str) -> str:
    """Searches the internet for real-time information."""
    return "Search results"


# 4. Triggers 'agentoscin:Team'
@CrewBase
class ComprehensiveCrew:
    """A highly complex team to test semantic mapping."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # Triggers 'agentoscin:LanguageModel'
    llm = "gpt-4-turbo"
    manager_llm = "gpt-4o"

    # Triggers 'agentoscin:LLMAgent', 'agentoscin:Goal', 'agentoscin:Prompt'
    @agent
    def primary_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["primary_researcher"],
            tools=[web_search],  # Triggers 'agentToolUsage'
            llm=self.llm,  # Triggers 'useLanguageModel'
            verbose=True,  # Triggers 'hasAgentConfig' (Config)
            memory=True,  # Triggers 'hasMemoryBinding' (Memory)
            knowledge=["Research_Database"],  # Triggers 'hasKnowledge'
        )

    @agent
    def senior_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_analyst"],
            tools=[DatabaseTool()],
            llm=self.llm,
            allow_delegation=False,  # Triggers 'hasAgentConfig'
        )

    # Triggers 'agentoscin:Task'
    @task
    def data_gathering(self) -> Task:
        return Task(
            config=self.tasks_config["data_gathering"],
            tools=[web_search],  # Triggers 'taskToolUsage'
        )

    @task
    def analysis_phase(self) -> Task:
        return Task(
            config=self.tasks_config["analysis_phase"],
            context=[self.data_gathering()],  # Triggers 'dependsOn'
            human_input=True,  # Triggers 'hasHumanCheckpoint'
            output_pydantic=AnalysisOutput,  # Triggers 'hasOutputSchema'
            guardrail=[lambda x: "error" not in x],  # Should trigger hasGuardrail
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,  # Triggers 'employsCoordinationPattern' (Hierarchical)
            manager_llm=self.manager_llm,
            memory=True,  # Triggers 'hasTeamMemoryBinding'
            verbose=True,  # Triggers 'hasSystemConfig'
        )
