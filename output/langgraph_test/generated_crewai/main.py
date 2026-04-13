"""
Auto-generated CrewAI Flow: StateGraph
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel




class StateGraphState(BaseModel):
    """Flow state — customize fields as needed."""
    messages: str = ""
    research_notes: str = ""
    final_summary: str = ""


class StateGraph(Flow[StateGraphState]):

    @start()
    def researcher(self):
        last_message = state['messages'][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return 'researcher'
        return 'writer'

    @listen(researcher)
    def writer(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
