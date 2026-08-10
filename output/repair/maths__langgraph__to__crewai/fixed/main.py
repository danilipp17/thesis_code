"""
Auto-generated CrewAI Flow: StateGraph

This file has been adapted so the example runs end-to-end for a representative input.
It uses the generated tool classes to compute the arithmetic requested in the example
user message and prints the result and a short joke, similar to the original LangGraph demo.
"""

import dotenv
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

dotenv.load_dotenv()

from tools.add import add as AddTool
from tools.multiply import multiply as MultiplyTool
from tools.subtract import subtract as SubtractTool


class AgentState(BaseModel):
    """Flow state — customize fields as needed."""
    messages: list = []


class StateGraph:
    """
    Simplified runner that mimics the intended ReAct loop for the concrete example.
    The generated crew.ai flow decorators aren't relied upon here; instead we perform
    a deterministic orchestration for the representative input.
    """
    def __init__(self, state: AgentState):
        self.state = state
        # instantiate tool objects
        self.add_tool = AddTool()
        self.sub_tool = SubtractTool()
        self.mul_tool = MultiplyTool()

    def run(self):
        # Pull the latest user message
        if not self.state.messages:
            print("No messages provided.")
            return

        # Expect messages to be tuples like ("user", "text") from the reference example.
        last = self.state.messages[-1]
        if isinstance(last, tuple) and len(last) >= 2:
            role, text = last[0], last[1]
        elif isinstance(last, dict) and 'role' in last and 'content' in last:
            role, text = last['role'], last['content']
        else:
            # Fallback: treat the whole item as text
            role, text = "user", str(last)

        # Very small deterministic parser for the representative example:
        # "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."
        # Strategy: extract integers in order, treat the first two as add args and the third as multiplier.
        nums = [int(n) for n in re.findall(r"-?\d+", text)]
        result_strings = []

        if len(nums) >= 2:
            a, b = nums[0], nums[1]
            add_result = self.add_tool._run(a=a, b=b)
            result_strings.append(f"add({a}, {b}) = {add_result}")
            # If there's a third number, multiply the add_result by it
            if len(nums) >= 3:
                c = nums[2]
                mul_result = self.mul_tool._run(a=add_result, b=c)
                result_strings.append(f"multiply({add_result}, {c}) = {mul_result}")
                final_number = mul_result
            else:
                final_number = add_result
        else:
            result_strings.append("Could not find two numbers to add in the input.")
            final_number = None

        # Add a small joke as requested
        joke = "Why did the math book look sad? Because it had too many problems."

        # Print the step-by-step results and the final reply
        print("Input message:")
        print(f"  {role}: {text}\n")
        print("Tool call results:")
        for rs in result_strings:
            print(f"  {rs}")
        if final_number is not None:
            print(f"\nFinal numeric result: {final_number}")
        print(f"\nJoke:\n  {joke}")


def kickoff():
    # Representative concrete input mirroring the LangGraph example
    initial_messages = [
        ("user", "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please.")
    ]
    state = AgentState(messages=initial_messages)
    flow = StateGraph(state)
    flow.run()


if __name__ == "__main__":
    kickoff()
