"""
Auto-generated CrewAI Flow: MathsFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.maths_crew.maths_crew import MathsCrew


class MathsState(BaseModel):
    """Flow state — customize fields as needed."""
    # Provide a representative concrete default query so the run is end-to-end.
    query: str = "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."
    answer: str = ""


class MathsFlow(Flow[MathsState]):

    @start()
    def reason_and_act(self):
        print("Kicking off MathsCrew...")
        # Pass the state's query into the crew so the agent has the input it expects.
        result = MathsCrew().crew().kickoff(inputs={"query": self.state.query})
        # Store a sensible string representation of the crew result in state.
        # The crew result shape may vary; try common attributes.
        self.state.answer = str(getattr(result, "raw", getattr(result, "output", result)))

    @listen(reason_and_act)
    def publish(self):
        print("Answer:")
        print(self.state.answer)


def kickoff():
    flow = MathsFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
