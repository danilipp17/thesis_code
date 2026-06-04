"""
travel-planning — CrewAI Flow port of the AutoGen original.

Original: examples/parallel/travel-planning/autogen — four AssistantAgents
(planner, local, language, summary) in a SelectorGroupChat coordinated
by a TextMentionTermination("TERMINATE") condition.

CrewAI mapping:
  - AssistantAgent          -> crewai.Agent
  - SelectorGroupChat       -> TravelPlanningCrew (Process.sequential)
                                (CrewAI has no selector-based routing;
                                 the four agents run in fixed order,
                                 documented as a thesis finding)
  - TextMentionTermination  -> implicit at end of last task
  - top-level Flow wraps the single crew, matching the other Flow ports.
"""

from crewai.flow.flow import Flow, listen, start
from dotenv import load_dotenv
from pydantic import BaseModel

from crews.travel_planning_crew.travel_planning_crew import TravelPlanningCrew

load_dotenv()


class TravelPlanningState(BaseModel):
    request: str = "Plan a 10 day trip to Luxembourg."
    plan: str = ""


class TravelPlanningFlow(Flow[TravelPlanningState]):
    """CrewAI Flow that orchestrates the TravelPlanningCrew."""

    @start()
    def plan_trip(self):
        print("Kicking off TravelPlanningCrew...")
        result = (
            TravelPlanningCrew()
            .crew()
            .kickoff(inputs={"request": self.state.request})
        )
        self.state.plan = str(result.raw)

    @listen(plan_trip)
    def publish(self):
        print("Final travel plan:")
        print(self.state.plan)


def kickoff():
    TravelPlanningFlow().kickoff()


if __name__ == "__main__":
    kickoff()
