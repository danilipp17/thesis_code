"""
Auto-generated CrewAI Flow: AutoGenFlow
"""

import dotenv
from typing import Any, Dict, List, Optional
import asyncio
import inspect
import sys

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

# Import the generated crew class
from crews.round_robin_group_chat.round_robin_group_chat import RoundRobinGroupChat

dotenv.load_dotenv()


class AutoGenFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class AutoGenFlow(Flow[AutoGenFlowState]):

    @start()
    def run_team(self):
        """
        Flow step that runs the RoundRobinGroupChat crew.
        Implemented to invoke the crew and print messages produced by the agents.
        """
        crew_base = RoundRobinGroupChat()
        crew = crew_base.crew()

        task_prompt = "Write a joke about cats, then improve and polish it."

        # Try to run the crew; handle sync/async returnables.
        result = crew.run(task=task_prompt)

        if inspect.isawaitable(result):
            result = asyncio.get_event_loop().run_until_complete(result)

        # Print a human-friendly representation of the result.
        printed_any = False
        try:
            # Common pattern: result.messages is a list of message objects
            messages = getattr(result, "messages", None)
            if messages is not None:
                for msg in messages:
                    # Support several possible message shapes
                    src = getattr(msg, "source", None) or msg.get("source") if isinstance(msg, dict) else None
                    content = getattr(msg, "content", None) or msg.get("content") if isinstance(msg, dict) else None
                    if src is None and hasattr(msg, "role"):
                        src = getattr(msg, "role")
                    if content is None and hasattr(msg, "text"):
                        content = getattr(msg, "text")
                    print(f"[{src}]: {content}")
                printed_any = True
            elif isinstance(result, (list, tuple)):
                for item in result:
                    if isinstance(item, dict):
                        src = item.get("source") or item.get("role") or item.get("sender")
                        content = item.get("content") or item.get("text") or item.get("message")
                        print(f"[{src}]: {content}")
                    else:
                        # Fallback to string representation
                        print(item)
                printed_any = True
            else:
                # Attempt to print other common fields
                if hasattr(result, "output"):
                    print(result.output)
                    printed_any = True
                elif hasattr(result, "text"):
                    print(result.text)
                    printed_any = True
        except Exception:
            # Fall back to a generic repr if anything unexpected arises
            pass

        if not printed_any:
            # Final fallback
            print("Crew run produced (raw):")
            print(result)


def kickoff():
    """
    Kickoff that directly runs the crew (bypasses Flow machinery for simplicity).
    This still uses the generated RoundRobinGroupChat crew so the agents will be
    invoked via the CrewAI framework and will call the configured LLM.
    """
    crew_base = RoundRobinGroupChat()
    crew = crew_base.crew()

    task_prompt = "Write a joke about cats, then improve and polish it."

    result = crew.run(task=task_prompt)

    # If the crew returns a coroutine, await it
    if inspect.isawaitable(result):
        result = asyncio.get_event_loop().run_until_complete(result)

    # Try to print messages in a robust way
    messages = getattr(result, "messages", None)
    if messages is not None:
        for msg in messages:
            src = getattr(msg, "source", None) or (msg.get("source") if isinstance(msg, dict) else None)
            content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
            if src is None and hasattr(msg, "role"):
                src = getattr(msg, "role")
            if content is None and hasattr(msg, "text"):
                content = getattr(msg, "text")
            print(f"[{src}]: {content}")
        return

    # If result is a list of dicts or strings
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, dict):
                src = item.get("source") or item.get("role") or item.get("sender")
                content = item.get("content") or item.get("text") or item.get("message")
                print(f"[{src}]: {content}")
            else:
                print(item)
        return

    # Other possible shapes
    if hasattr(result, "output"):
        print(result.output)
        return
    if hasattr(result, "text"):
        print(result.text)
        return

    # Generic fallback
    print("Crew run produced (raw):")
    print(result)


if __name__ == "__main__":
    kickoff()
