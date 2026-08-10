"""
Auto-generated CrewAI Flow: JokeFlow
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.generate_joke_crew.generate_joke_crew import GenerateJokeCrew
from crews.improve_joke_crew.improve_joke_crew import ImproveJokeCrew
from crews.polish_joke_crew.polish_joke_crew import PolishJokeCrew


class JokeState(BaseModel):
    """Flow state — customize fields as needed."""
    final_joke: str = ""
    improved_joke: str = ""
    joke: str = ""
    topic: str = "cats"


class JokeFlow(Flow[JokeState]):

    @start()
    def generate_joke(self):
        result = GenerateJokeCrew().crew().kickoff(inputs={"topic": self.state.topic})
        # Save the generated joke into state for routing / downstream steps
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
        result = PolishJokeCrew().crew().kickoff(inputs={"improved_joke": self.state.improved_joke})
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
