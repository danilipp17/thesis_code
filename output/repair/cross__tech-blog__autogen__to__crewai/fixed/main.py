"""
Auto-generated CrewAI Flow: AutoGenFlow

This entrypoint will instantiate the generated RoundRobinGroupChat crew and run it
on the sample task. The crew's agents will perform LLM calls via the CrewAI framework
at runtime; results are printed to stdout.
"""

import dotenv
import asyncio
import inspect
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

from crews.round_robin_group_chat.round_robin_group_chat import RoundRobinGroupChat

class AutoGenFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class AutoGenFlow(Flow[AutoGenFlowState]):

    @start()
    def run_team(self):
        # This flow node is intentionally left as an empty orchestration placeholder.
        # The actual crew run is performed in kickoff() below to ensure the program
        # executes end-to-end when invoked as __main__.
        return None


def kickoff():
    # Instantiate the generated crew class and build the Crew object.
    rr = RoundRobinGroupChat()
    crew = rr.crew()

    task_text = "We need a blog post about Agentic AI Frameworks. Please research, write, and edit."

    # The Crew.run() method may be synchronous or async depending on the runtime.
    # Call it and handle either case. The crew framework will make live LLM calls.
    try:
        result = crew.run(task=task_text)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
    except TypeError:
        # Some Crew implementations expect positional task argument or different call shape.
        # Try alternate invocation patterns.
        try:
            result = crew.run(task_text)
            if inspect.isawaitable(result):
                result = asyncio.run(result)
        except Exception as e:
            # If running via crew.run fails in an unexpected way, raise to surface the error.
            raise

    # Print the result in a readable way. Many crew run results include a .messages list.
    if hasattr(result, "messages"):
        for msg in result.messages:
            source = getattr(msg, "source", getattr(msg, "role", "agent"))
            content = getattr(msg, "content", str(msg))
            print(f"[{source}]: {content}")
    else:
        # Fallback: print the raw result object
        print(result)


if __name__ == "__main__":
    kickoff()
