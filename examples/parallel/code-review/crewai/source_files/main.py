"""
code-review — CrewAI Flow port of the AutoGen original.

Original: examples/autogen/code-review/source_files/main.py — three
AssistantAgents in RoundRobinGroupChat with a shared FunctionTool.

CrewAI mapping:
  - AssistantAgent              -> crewai.Agent (role/goal/backstory in YAML)
  - RoundRobinGroupChat         -> CodeReviewCrew (Process.sequential)
  - FunctionTool(code_analyzer) -> @tool-decorated code_analyzer
  - implicit chat passing       -> explicit Task objects with context=[...]
  - reviewer + auditor share the tool; summarizer has none (preserved).
  - the top-level Flow exists for parity with the other Flow examples
    (single @start kicks off the crew).
"""

from crewai.flow.flow import Flow, listen, start
from dotenv import load_dotenv
from pydantic import BaseModel

from crews.code_review_crew.code_review_crew import CodeReviewCrew

load_dotenv()


CODE_TO_REVIEW = """
def process_user_input(data):
    result = eval(data)
    return result
"""


class CodeReviewState(BaseModel):
    code: str = CODE_TO_REVIEW
    report: str = ""


class CodeReviewFlow(Flow[CodeReviewState]):
    """CrewAI Flow that orchestrates the CodeReviewCrew."""

    @start()
    def review(self):
        print("Kicking off CodeReviewCrew...")
        result = CodeReviewCrew().crew().kickoff(inputs={"code": self.state.code})
        self.state.report = str(result.raw)

    @listen(review)
    def publish(self):
        print("Code review complete:")
        print(self.state.report)


def kickoff():
    CodeReviewFlow().kickoff()


if __name__ == "__main__":
    kickoff()
