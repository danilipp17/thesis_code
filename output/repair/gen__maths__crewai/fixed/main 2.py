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
    answer: str = ""
    query: str = (
        "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."
    )


class MathsFlow(Flow[MathsState]):

    @start()
    def reason_and_act(self):
        print("Kicking off MathsCrew...")
        # Provide the query from the flow state to the crew kickoff.
        result = MathsCrew().crew().kickoff(inputs={"query": self.state.query})
        # The CrewAI kickoff result exposes a .raw attribute with the final output.
        # Store it in state and return it.
        try:
            self.state.answer = str(result.raw)
        except Exception:
            # Fall back to str(result) if .raw not present.
            self.state.answer = str(result)
        return result

    @listen(reason_and_act)
    def publish(self):
        print("Answer:")
        print(self.state.answer)


def kickoff():
    flow = MathsFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
