"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class TechBlogState(BaseModel):
    """Flow state — customize fields as needed."""
    draft: str = ""
    final_post: str = ""
    messages: list = []
    research: str = ""
    topic: str = ""


class StateGraph(Flow[TechBlogState]):

    @start()
    def researcher(self):
        pass  # TODO: implement step logic

    @listen(researcher)
    def writer(self):
        pass  # TODO: implement step logic

    @listen(writer)
    def editor(self):
        pass  # TODO: implement step logic


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
