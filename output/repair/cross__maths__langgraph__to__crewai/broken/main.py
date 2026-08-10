"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class AgentState(BaseModel):
    """Flow state — customize fields as needed."""
    messages: list = []


class StateGraph(Flow[AgentState]):

    @start()
    def our_agent(self):
        last_message = self.state['messages'][-1]

    @listen(our_agent)
    def tools(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
