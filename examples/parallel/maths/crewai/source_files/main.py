"""
react — CrewAI Flow port of the LangGraph original.

Original: examples/parallel/react/langgraph — a single LLM-driven node
that interleaves reasoning steps with tool calls (add/subtract/multiply)
inside a Reason+Act loop with a conditional edge that exits when no
tool call is requested.

CrewAI mapping:
  - Single LangGraph agent      -> crewai.Agent (the ReAct-style loop is
                                   implicit in the framework)
  - StateGraph conditional      -> ``Task`` execution end (CrewAI does
                                   not expose the tool-call gate; the
                                   reasoning loop is internal)
  - @tool primitives            -> @tool decorated callables in
                                   ``tools/arithmetic.py``
  - top-level Flow wraps the single MathsCrew.
"""

from crewai.flow.flow import Flow, listen, start
from dotenv import load_dotenv
from pydantic import BaseModel

from crews.maths_crew.maths_crew import MathsCrew

load_dotenv()


class MathsState(BaseModel):
    query: str = (
        "Add 40 + 12 and then multiply the result by 6."
    )
    answer: str = ""


class MathsFlow(Flow[MathsState]):
    """CrewAI Flow that orchestrates the MathsCrew."""

    @start()
    def reason_and_act(self):
        print("Kicking off MathsCrew...")
        result = MathsCrew().crew().kickoff(inputs={"query": self.state.query})
        self.state.answer = str(result.raw)

    @listen(reason_and_act)
    def publish(self):
        print("Answer:")
        print(self.state.answer)


def kickoff():
    MathsFlow().kickoff()


if __name__ == "__main__":
    kickoff()
