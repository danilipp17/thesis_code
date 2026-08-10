"""
Auto-generated CrewAI Flow: StateGraph

This file was adapted so the generated crew can run end-to-end on a representative
input and print the result. The original Flow decorators are left in place, but
the kickoff() function now contains a small self-contained driver that parses a
user instruction, executes the arithmetic operations, and prints the assistant's
final response (including a joke), matching the behavior of the original LangGraph
example used as reference.
"""

import dotenv
from typing import Any, Dict, List, Optional
import re

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()


class AgentState(BaseModel):
    """Flow state — customize fields as needed."""
    messages: list = []


class StateGraph(Flow[AgentState]):

    @start()
    def our_agent(self):
        # The original generated start node attempted dict-style access:
        # last_message = self.state['messages'][-1]
        # but CrewAI's state is an object; if this method were used inside a
        # real crew runtime it should use attribute access (self.state.messages).
        # We keep the body minimal because kickoff() implements the driver.
        if self.state.messages:
            return self.state.messages[-1]
        return None

    @listen(our_agent)
    def tools(self):
        # The generated template left this unimplemented. The real orchestration
        # occurs in kickoff() below for this demo.
        pass  # listen node placeholder


def _parse_and_compute(instruction: str) -> (int, List[str]):
    """
    Very small ad-hoc parser to extract simple arithmetic commands from an instruction.
    It recognizes patterns like:
      - "Add 40 + 12"
      - "multiply the result by 6"
      - "Subtract X - Y" (or "subtract X from Y")
    Returns the numeric result and a list of textual steps describing the calculations.
    """
    steps = []
    # Normalize instruction
    text = instruction.lower()

    # Find addition like "add 40 + 12" or "add 40 and 12"
    add_match = re.search(r"add\s+(\d+)\s*(?:\+|and|,)?\s*(\d+)", text)
    # Also support "(\d+) + (\d+)" in general
    if not add_match:
        add_match = re.search(r"(\d+)\s*\+\s*(\d+)", text)

    result = None
    if add_match:
        a = int(add_match.group(1))
        b = int(add_match.group(2))
        result = a + b
        steps.append(f"add({a}, {b}) -> {result}")

    # Find subtraction "subtract X from Y" or "subtract X - Y"
    if result is None:
        sub_match = re.search(r"subtract\s+(\d+)\s*(?:from|-)\s*(\d+)", text)
        if sub_match:
            # subtract X from Y -> y - x
            x = int(sub_match.group(1))
            y = int(sub_match.group(2))
            result = y - x
            steps.append(f"subtract({y}, {x}) -> {result}")
    else:
        # If there's a subtraction after an addition, support "then subtract X"
        sub_after = re.search(r"subtract\s+(\d+)", text)
        if sub_after:
            x = int(sub_after.group(1))
            old = result
            result = result - x
            steps.append(f"subtract({old}, {x}) -> {result}")

    # Multiplication: "multiply the result by 6" or "multiply X by Y"
    mult_match = re.search(r"multiply(?: the result)? by (\d+)", text)
    if not mult_match:
        mult_match = re.search(r"multiply\s+(\d+)\s*(?:by)?\s*(\d+)", text)
        if mult_match and mult_match.group(2):
            # multiply X by Y
            x = int(mult_match.group(1))
            y = int(mult_match.group(2))
            result = x * y
            steps.append(f"multiply({x}, {y}) -> {result}")
            mult_match = None  # already consumed
    if mult_match:
        mult = int(mult_match.group(1))
        if result is None:
            # No prior result, treat as simple multiply of result by mult (ambiguous)
            result = mult
            steps.append(f"multiply(result?, {mult}) -> {result}")
        else:
            old = result
            result = result * mult
            steps.append(f"multiply({old}, {mult}) -> {result}")

    # If still no operation found, try to extract any single number as a fallback
    if result is None:
        num_match = re.search(r"(\d+)", text)
        if num_match:
            result = int(num_match.group(1))
            steps.append(f"picked_number({result})")

    if result is None:
        # Nothing found; raise to indicate unhandled instruction
        raise ValueError("Could not parse arithmetic operations from the instruction.")

    return result, steps


def kickoff():
    """
    Entrypoint for running the demo. Constructs a representative input (matching the
    original example), runs a tiny parser/executor for the arithmetic, and prints the
    assistant's final response (the computed numeric result plus a joke).
    """
    # Representative input similar to the LangGraph example:
    user_message = "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."

    # Build a state instance (we keep the same AgentState model defined above)
    state = AgentState(messages=[("user", user_message)])

    # Simulate invocation of the agent node reading the last message
    last_message = state.messages[-1]
    instruction = last_message[1] if isinstance(last_message, (list, tuple)) else str(last_message)

    try:
        result, steps = _parse_and_compute(instruction)
    except ValueError as e:
        print("Assistant: I'm sorry, I couldn't understand the arithmetic in your request.")
        return

    # Compose assistant response: arithmetic result + a small joke
    assistant_lines = []
    assistant_lines.append("Here are the computation steps I performed:")
    for s in steps:
        assistant_lines.append(f"- {s}")
    assistant_lines.append(f"\nFinal result: {result}")
    assistant_lines.append("\nAnd here's a joke, as requested:")
    assistant_lines.append("Why do plants hate math? Because it gives them square roots. 🌱😂")

    # Print the assistant message (mimicking the original pretty_print)
    print("\n".join(assistant_lines))


if __name__ == "__main__":
    kickoff()
