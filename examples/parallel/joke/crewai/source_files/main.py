"""
joke — CrewAI Flow port of the LangGraph original.

Original: examples/langgraph/joke/joke.py — three-step refinement
(generate → conditional skip-or-improve → polish).

CrewAI mapping:
  - StateGraph              -> crewai.flow.flow.Flow
  - TypedDict State         -> pydantic JokeState
  - add_node                -> @start / @listen decorated methods
  - conditional_edges       -> @router(generate_joke) returning "Pass"/"Fail"
  - each node's llm.invoke  -> a sub-Crew under crews/<step>_crew/
                                (one agent + one task, both YAML-configured).
"""

from crewai.flow.flow import Flow, listen, router, start
from dotenv import load_dotenv
from pydantic import BaseModel

from crews.generate_joke_crew.generate_joke_crew import GenerateJokeCrew
from crews.improve_joke_crew.improve_joke_crew import ImproveJokeCrew
from crews.polish_joke_crew.polish_joke_crew import PolishJokeCrew

load_dotenv()


class JokeState(BaseModel):
    topic: str = "cats"
    joke: str = ""
    improved_joke: str = ""
    final_joke: str = ""


class JokeFlow(Flow[JokeState]):
    """CrewAI Flow equivalent of the LangGraph joke StateGraph."""

    @start()
    def generate_joke(self):
        result = GenerateJokeCrew().crew().kickoff(inputs={"topic": self.state.topic})
        self.state.joke = str(result.raw)

    @router(generate_joke)
    def check_punchline(self):
        """Gate function: skip improvements if the joke already has a punchline."""
        if "?" in self.state.joke or "!" in self.state.joke:
            return "Pass"
        return "Fail"

    @listen("Fail")
    def improve_joke(self):
        result = ImproveJokeCrew().crew().kickoff(inputs={"joke": self.state.joke})
        self.state.improved_joke = str(result.raw)

    @listen(improve_joke)
    def polish_joke(self):
        result = (
            PolishJokeCrew()
            .crew()
            .kickoff(inputs={"improved_joke": self.state.improved_joke})
        )
        self.state.final_joke = str(result.raw)


def kickoff():
    flow = JokeFlow()
    flow.kickoff()
    print("Initial joke:")
    print(flow.state.joke)
    if flow.state.improved_joke:
        print("\n--- --- ---\nImproved joke:")
        print(flow.state.improved_joke)
        print("\n--- --- ---\nFinal joke:")
        print(flow.state.final_joke)
    else:
        print("\n(joke already had a punchline — improvements skipped)")


if __name__ == "__main__":
    kickoff()
