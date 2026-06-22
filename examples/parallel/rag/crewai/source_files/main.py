"""
rag — CrewAI Flow port of the LangGraph original.

Original: examples/parallel/rag/langgraph — a single LLM agent in a
ReAct loop with one retriever_tool over a Stock Market 2024 PDF.

CrewAI mapping:
  - LangGraph llm node + ReAct loop -> a single-agent RagCrew (the
    tool-call loop is implicit in the framework).
  - LangGraph retriever_tool        -> @tool callable in
                                       tools/retriever.py.
  - top-level Flow wraps the single RagCrew with a fixed question.
"""

from crewai.flow.flow import Flow, listen, start
from dotenv import load_dotenv
from pydantic import BaseModel

from crews.rag_crew.rag_crew import RagCrew

load_dotenv()


class RagState(BaseModel):
    question: str = "How did the stock market perform in 2024?"
    answer: str = ""


class RagFlow(Flow[RagState]):
    """CrewAI Flow that orchestrates the RagCrew."""

    @start()
    def answer(self):
        print("Kicking off RagCrew...")
        result = RagCrew().crew().kickoff(inputs={"question": self.state.question})
        self.state.answer = str(result.raw)

    @listen(answer)
    def publish(self):
        print("Answer:")
        print(self.state.answer)


def kickoff():
    RagFlow().kickoff()


if __name__ == "__main__":
    kickoff()
