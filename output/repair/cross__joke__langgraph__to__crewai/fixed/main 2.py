"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class State(BaseModel):
    """Flow state — customize fields as needed."""
    final_joke: str = ""
    improved_joke: str = ""
    joke: str = ""
    topic: str = ""


class StateGraph(Flow[State]):

    @start()
    def generate_joke(self):
        # Create an initial joke deterministically based on the topic.
        topic = self.state.topic or "cats"

        # Intentionally create a simple initial joke WITHOUT '?' or '!' so
        # we exercise the improve -> polish path for the representative input.
        initial = f"A {topic} sat on a keyboard because it was trying to keep up with the mouse."
        self.state.joke = initial

        # Print initial joke
        print("Initial joke:")
        print(self.state.joke)
        print("\n--- --- ---\n")

        # Check punchline: presence of '?' or '!' means we consider it finished.
        if "?" in self.state.joke or "!" in self.state.joke:
            # Directly finalize
            self.state.final_joke = self.state.joke
            print("Final joke:")
            print(self.state.final_joke)
            return

        # Otherwise, run the improvement and polishing steps sequentially.
        self.improve_joke()
        # After improvement, print intermediate
        if self.state.improved_joke:
            print("Improved joke:")
            print(self.state.improved_joke)
            print("\n--- --- ---\n")

        self.polish_joke()

        # Print final joke
        print("Final joke:")
        # If polish step produced a final_joke, show it; otherwise fall back.
        print(self.state.final_joke or self.state.improved_joke or self.state.joke)


    def improve_joke(self):
        # Simple deterministic improvement: add wordplay related to topic.
        if not self.state.joke:
            return
        # Add a bit of wordplay
        self.state.improved_joke = (
            f"{self.state.joke} It was purr-fect at catching the mouse and always landed on its feet."
        )


    def polish_joke(self):
        # Final polish: add a surprising twist.
        if self.state.improved_joke:
            self.state.final_joke = (
                f"{self.state.improved_joke} But in the end it resigned — it preferred cat naps to cat calls."
            )
        elif self.state.joke:
            # If no improved joke exists, lightly polish the original.
            self.state.final_joke = f"{self.state.joke} And that was the last time the mouse clicked."



def kickoff():
    flow = StateGraph()
    # Provide a representative concrete input (like the original example).
    flow.state.topic = "cats"
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
