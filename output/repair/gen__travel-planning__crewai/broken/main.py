"""
Auto-generated CrewAI Flow: TravelPlanningFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.travel_planning_crew.travel_planning_crew import TravelPlanningCrew


class TravelPlanningState(BaseModel):
    """Flow state — customize fields as needed."""
    plan: str = ""
    request: str = ""


class TravelPlanningFlow(Flow[TravelPlanningState]):

    @start()
    def plan_trip(self):
        result = TravelPlanningCrew().crew().kickoff()
        return result

    @listen(plan_trip)
    def publish(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = TravelPlanningFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
