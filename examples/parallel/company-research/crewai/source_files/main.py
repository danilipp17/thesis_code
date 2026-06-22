"""
company-research — CrewAI Flow port of the AutoGen original.

Original: examples/parallel/company-research/autogen — a
RoundRobinGroupChat of three AssistantAgents (web search, stock
analysis, report) producing a financial report.

CrewAI mapping:
  - AutoGen RoundRobinGroupChat -> a sequential CompanyResearchCrew
    whose three agents run in order (search -> analysis -> report).
  - AutoGen AssistantAgents     -> crewai.Agent (search_agent,
                                   analysis_agent, report_agent).
  - AutoGen FunctionTools       -> @tool callables in
                                   tools/research_tools.py.
  - top-level Flow wraps the single CompanyResearchCrew.
"""

from crewai.flow.flow import Flow, listen, start
from dotenv import load_dotenv
from pydantic import BaseModel

from crews.company_research_crew.company_research_crew import CompanyResearchCrew

load_dotenv()


class CompanyResearchState(BaseModel):
    company: str = "American Airlines"
    report: str = ""


class CompanyResearchFlow(Flow[CompanyResearchState]):
    """CrewAI Flow that orchestrates the CompanyResearchCrew."""

    @start()
    def research_company(self):
        print("Kicking off CompanyResearchCrew...")
        result = (
            CompanyResearchCrew()
            .crew()
            .kickoff(inputs={"company": self.state.company})
        )
        self.state.report = str(result.raw)

    @listen(research_company)
    def publish(self):
        print("Financial report:")
        print(self.state.report)


def kickoff():
    CompanyResearchFlow().kickoff()


if __name__ == "__main__":
    kickoff()
