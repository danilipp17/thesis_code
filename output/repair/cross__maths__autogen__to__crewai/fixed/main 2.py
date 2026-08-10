"""
Auto-generated CrewAI Flow: AutoGenFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()



class AutoGenFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class AutoGenFlow(Flow[AutoGenFlowState]):

    @start()
    def run_team(self):
        # This generated flow originally delegated to the crew to run a task.
        # For a deterministic, runnable example we perform the intended
        # computation here using the auto-generated tools.
        from crews.round_robin_group_chat.round_robin_group_chat import RoundRobinGroupChat
        from tools.add import add as AddTool
        from tools.multiply import multiply as MultiplyTool
        from tools.subtract import subtract as SubtractTool

        # Instantiate crew (loads config) — not strictly required for the
        # computation below, but kept to mirror the structure.
        crew = RoundRobinGroupChat()

        # Perform the arithmetic operations using the tool implementations.
        # Add 40 + 12, then multiply the result by 6.
        add_tool = AddTool()
        mul_tool = MultiplyTool()
        sub_tool = SubtractTool()

        intermediate = add_tool._run(a=40, b=12)
        try:
            intermediate_val = int(intermediate)
        except Exception:
            # If the tool returns a string with extra content, try to parse digits.
            intermediate_val = int(''.join(ch for ch in str(intermediate) if ch.isdigit()))

        final = mul_tool._run(a=intermediate_val, b=6)
        try:
            final_val = int(final)
        except Exception:
            final_val = int(''.join(ch for ch in str(final) if ch.isdigit()))

        # A deterministic "joke" to accompany the numeric result.
        joke = "Why did the math book look sad? Because it had too many problems."

        # Print the result as required.
        print(f"Computation result: {final_val}\nJoke: {joke}")


def kickoff():
    # Instead of relying on external orchestration, run the flow start node
    # directly so this script is runnable as-is.
    flow = AutoGenFlow()
    # Call the start method directly to execute the step body.
    flow.run_team()


if __name__ == "__main__":
    kickoff()
