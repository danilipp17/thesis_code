"""
Auto-generated CrewAI Flow: StateGraph

This launcher loads the auto-generated Crew (from crews/state_graph/state_graph.py)
and runs it end-to-end with a representative input (topic="cats"), then prints the
resulting joke state. It attempts multiple common Crew run method names to be
robust to different crewai versions.
"""

import dotenv
import inspect
import asyncio
from typing import Any

dotenv.load_dotenv()


def _call_maybe_async(fn, *args, **kwargs):
    """Call a function that might be a coroutine function."""
    if inspect.iscoroutinefunction(fn):
        return asyncio.run(fn(*args, **kwargs))
    return fn(*args, **kwargs)


def _extract_text_from_state(state: Any) -> str:
    """Try to find the final joke text in various possible return shapes."""
    # If it's a dict-like
    try:
        if isinstance(state, dict):
            # Prefer final_joke, then improved_joke, then joke
            for key in ("final_joke", "improved_joke", "joke"):
                if key in state and state[key]:
                    return state[key]
            # fallback: pretty print dict
            return str(state)
        # If it's a pydantic model or object with attributes
        for attr in ("final_joke", "improved_joke", "joke"):
            if hasattr(state, attr):
                val = getattr(state, attr)
                if val:
                    return val
        # If it has a .state attribute
        if hasattr(state, "state"):
            return _extract_text_from_state(getattr(state, "state"))
        # If it is a simple string
        if isinstance(state, str):
            return state
    except Exception:
        pass
    # Last resort representation
    return repr(state)


def kickoff():
    # Import the auto-generated crew class (CrewBase) and instantiate it.
    # We import here to avoid altering the module-level imports in the generated file.
    from crews.state_graph import state_graph as crew_module

    # The generated crew class is named StateGraph in that module.
    CrewClass = getattr(crew_module, "StateGraph")

    # Instantiate the crew base and build the Crew instance using its crew() method.
    crew_base = CrewClass()
    crew_obj = crew_base.crew()

    # Prepare a representative input state
    initial_input = {"topic": "cats"}

    # Try a list of common runner method names used by different crewai versions.
    runner_candidates = [
        "run_stream",
        "run",
        "kickoff",
        "start",
        "execute",
        "__call__",
    ]

    result = None
    last_error = None

    for name in runner_candidates:
        if not hasattr(crew_obj, name):
            continue
        fn = getattr(crew_obj, name)
        try:
            # Try calling with the initial input first
            try:
                result = _call_maybe_async(fn, initial_input)
            except TypeError:
                # If signature doesn't accept args, try calling without args
                result = _call_maybe_async(fn)
            break
        except Exception as e:
            last_error = e
            # try next candidate
            continue

    if result is None:
        # If we couldn't run any method, raise informative error
        raise RuntimeError(
            "Could not run the Crew. Tried methods: "
            f"{runner_candidates}. Last error: {last_error}"
        )

    # Extract the best-guess joke text from the returned state
    joke_text = _extract_text_from_state(result)

    # Print the result (ensures output is produced at runtime by the crew execution)
    print("Final joke (extracted):")
    print(joke_text)


if __name__ == "__main__":
    kickoff()
