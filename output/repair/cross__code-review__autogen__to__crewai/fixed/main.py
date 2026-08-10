"""
Auto-generated CrewAI Flow: AutoGenFlow
"""

import dotenv
from typing import Any, Dict, List, Optional
import inspect
import asyncio

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()


class AutoGenFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class AutoGenFlow(Flow[AutoGenFlowState]):

    @start()
    def run_team(self):
        # Instantiate the generated crew and run it with a concrete task.
        # We attempt several common runner method names on the Crew object so
        # this works across small API differences in Crew implementations.
        from crews.round_robin_group_chat.round_robin_group_chat import RoundRobinGroupChat

        code_to_review = """
def process_user_input(data):
    result = eval(data)
    return result
"""
        rr = RoundRobinGroupChat()
        crew_obj = rr.crew()

        task_prompt = f"Review the following code for quality and security:\n{code_to_review}"

        runner_methods = ("run", "kickoff", "start", "execute", "execute_task", "launch")
        result = None
        for name in runner_methods:
            if hasattr(crew_obj, name):
                method = getattr(crew_obj, name)
                try:
                    maybe_result = method(task=task_prompt)
                except TypeError:
                    maybe_result = method(task_prompt)
                # If coroutine, run it to completion
                if inspect.isawaitable(maybe_result):
                    try:
                        maybe_result = asyncio.get_event_loop().run_until_complete(maybe_result)
                    except RuntimeError:
                        # no running loop, create one
                        maybe_result = asyncio.run(maybe_result)
                result = maybe_result
                break

        # If no runner method, try calling crew object directly if callable
        if result is None:
            if callable(crew_obj):
                maybe_result = crew_obj(task_prompt)
                if inspect.isawaitable(maybe_result):
                    try:
                        maybe_result = asyncio.get_event_loop().run_until_complete(maybe_result)
                    except RuntimeError:
                        maybe_result = asyncio.run(maybe_result)
                result = maybe_result
            else:
                print("Could not find a runnable method on Crew. Exiting.")
                return

        # Print whatever the crew returned (could be None)
        print(result)


def kickoff():
    flow = AutoGenFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
