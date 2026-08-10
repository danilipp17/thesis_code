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
    topic: str = ""


class JokeFlow(Flow[JokeState]):

    @start()
    def generate_joke(self):
        result = GenerateJokeCrew().crew().kickoff()
        return result

    @router(generate_joke)
    def check_punchline(self):
        """Gate function: skip improvements if the joke already has a punchline."""
        if "?" in self.state.joke or "!" in self.state.joke:
            return "Pass"
        return "Fail"

    @listen("Fail")
    def improve_joke(self):
        result = ImproveJokeCrew().crew().kickoff()
        return result

    @listen(improve_joke)
    def polish_joke(self):
        result = PolishJokeCrew().crew().kickoff()
        return result


def kickoff():
    flow = JokeFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
