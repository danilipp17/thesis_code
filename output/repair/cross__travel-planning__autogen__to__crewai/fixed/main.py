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
    def run_group_chat(self):
        # Instantiate the generated crew and run it with the intended task.
        # Try several common runtime entrypoints on the Crew object to be robust.
        from crews.selector_group_chat.selector_group_chat import SelectorGroupChat
        import inspect
        import asyncio
        import json

        task_prompt = "Plan a 10 day trip to Luxembourg."

        sg = SelectorGroupChat()
        crew_obj = sg.crew()

        run_methods = ["run_stream", "run", "start", "execute", "invoke"]
        result = None
        last_exc = None

        for m in run_methods:
            if hasattr(crew_obj, m):
                try:
                    method = getattr(crew_obj, m)
                    out = method(task=task_prompt)
                    if inspect.isawaitable(out):
                        # If an event loop is already running, use create_task & gather pattern,
                        # but usually kickoff is synchronous so run_until_complete works.
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # If loop is running, create a new task and wait for it
                                fut = asyncio.ensure_future(out)
                                loop.run_until_complete(fut)
                                out = fut.result()
                            else:
                                out = loop.run_until_complete(out)
                        except RuntimeError:
                            # No running loop, create one
                            out = asyncio.run(out)
                    result = out
                    break
                except Exception as e:
                    last_exc = e
                    continue

        if result is None:
            # Fallback: try calling crew as a callable or show an informative error
            try:
                out = crew_obj(task=task_prompt)
                if inspect.isawaitable(out):
                    out = asyncio.run(out)
                result = out
            except Exception as e:
                result = f"Failed to run crew: {e}. Last run attempt exception: {last_exc}"

        # Print the result. If it's structured, pretty-print as JSON.
        if isinstance(result, (dict, list)):
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result)


def kickoff():
    flow = AutoGenFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
