"""
Auto-generated CrewAI Flow: AutoGenFlow
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
        Kick off the RoundRobinGroupChat crew and print the produced result.

        We attempt a few likely runner method names on the Crew object (and,
        as fallback, on the Agent) because generated code targets the CrewAI
        runtime and different versions expose slightly different entry points.
        """
        import asyncio
        import inspect

        # Import the crew base class and instantiate it
        from crews.round_robin_group_chat.round_robin_group_chat import RoundRobinGroupChat

        rr = RoundRobinGroupChat()
        crew = rr.crew()

        task_text = (
            "Add 40 + 12 and then multiply the result by 6. Also tell me a joke please."
        )

        result = None

        # Helper to call a callable, handling async/sync transparently.
        def call_maybe_async(fn, *args, **kwargs):
            try:
                res = fn(*args, **kwargs)
            except TypeError:
                # try without kwargs
                res = fn(*args)
            if inspect.isawaitable(res):
                # run the coroutine to completion
                return asyncio.get_event_loop().run_until_complete(res)
            return res

        # Try common crew entry points
        crew_methods = ("run_stream", "run", "kickoff", "start", "execute", "invoke", "launch")
        for m in crew_methods:
            if hasattr(crew, m):
                try:
                    fn = getattr(crew, m)
                    result = call_maybe_async(fn, task_text)
                    break
                except Exception:
                    # If this method failed, continue to try others.
                    continue

        # Fallback: try invoking the single agent directly
        if result is None:
            agent = rr.our_agent()
            agent_methods = ("run_stream", "run", "invoke", "start", "chat", "converse", "complete")
            for m in agent_methods:
                if hasattr(agent, m):
                    try:
                        fn = getattr(agent, m)
                        # many agent methods accept either a single string or a named task kw
                        try:
                            result = call_maybe_async(fn, task_text)
                        except TypeError:
                            result = call_maybe_async(fn, task=task_text)
                        break
                    except Exception:
                        continue

        # As a final fallback, attempt to call a generic "kickoff" on the crew base
        if result is None and hasattr(rr, "crew"):
            try:
                # Some older/generated APIs expect a kickoff or run without args
                if hasattr(crew, "kickoff"):
                    result = call_maybe_async(getattr(crew, "kickoff"))
            except Exception:
                result = None

        # Print whatever we got. This must be produced by the model or the crew runtime.
        print(result)


def kickoff():
    flow = AutoGenFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
