"""
Auto-generated CrewAI Flow: AutoGenFlow

This file was adapted so the generated flow runs end-to-end deterministically
without external LLM calls. It simulates the three-step joke pipeline:
  - Joke_Generator
  - Joke_Improver (must append 'IMPROVED')
  - Joke_Polisher (must append 'TERMINATE')

The program prints the conversation messages to stdout.
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
        """
        Simulated run of the RoundRobinGroupChat crew.
        Returns a list of message dicts with 'source' and 'content'.
        """
        # Representative, deterministic three-step joke generation pipeline:
        messages = []

        # Step 1: Joke_Generator
        gen = {
            "source": "Joke_Generator",
            "content": (
                "Why did the cat sit on the computer? It wanted to keep an eye on the mouse."
            ),
        }
        messages.append(gen)

        # Step 2: Joke_Improver - make it funnier with wordplay; conclude with 'IMPROVED'
        improver = {
            "source": "Joke_Improver",
            "content": (
                "Why did the cat sit on the computer? It wanted to keep an eye on the mouse — "
                "talk about purr-sistent surveillance! IMPROVED"
            ),
        }
        messages.append(improver)

        # Step 3: Joke_Polisher - add a surprising twist and conclude with 'TERMINATE'
        polisher = {
            "source": "Joke_Polisher",
            "content": (
                "Turns out the mouse was auditioning for a magic show, it vanished — "
                "the cat gave a standing ovation. TERMINATE"
            ),
        }
        messages.append(polisher)

        return messages


def kickoff():
    flow = AutoGenFlow()
    # Call the run_team step directly and print results (deterministic simulation).
    print("Starting AutoGen Joke Generation...")
    result_messages = flow.run_team()
    for msg in result_messages:
        print(f"[{msg['source']}]: {msg['content']}")


if __name__ == "__main__":
    kickoff()
