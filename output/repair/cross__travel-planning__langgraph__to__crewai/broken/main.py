"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class TravelState(BaseModel):
    """Flow state — customize fields as needed."""
    final_plan: str = ""
    language_notes: str = ""
    local_notes: str = ""
    plan: str = ""
    request: str = ""


class StateGraph(Flow[TravelState]):

    @start()
    def planner_agent(self):
        pass  # TODO: implement step logic

    @listen(planner_agent)
    def local_agent(self):
        pass  # TODO: implement step logic

    @listen(local_agent)
    def language_agent(self):
        pass  # TODO: implement step logic

    @listen(language_agent)
    def travel_summary_agent(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
