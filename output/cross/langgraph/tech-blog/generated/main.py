"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class StateGraphState(BaseModel):
    """Flow state — customize fields as needed."""
    messages: Annotated[Sequence[BaseMessage], operator.add] = None
    research: str = ""
    draft: str = ""
    final_post: str = ""
    topic: str = ""


class StateGraph(Flow[StateGraphState]):

    @start()
    def researcher(self):
        pass  # TODO: implement step logic

    @listen(researcher)
    def writer(self):
        pass  # TODO: implement step logic

    @listen()
    def editor(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
