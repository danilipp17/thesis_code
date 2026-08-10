"""
Auto-generated AutoGen application: joke
"""

import asyncio
import dotenv
from typing import Any, Dict, List, Optional

dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


model_client = OpenAIChatCompletionClient(model="gpt-4o")


# -- Agents --
joke_generator = AssistantAgent(
    name="Joke_Generator",
    model_client=model_client,
    system_message=(
        "Write a short joke on the given topic. A witty comedian who comes up with sharp, short jokes."
    ),
)

joke_improver = AssistantAgent(
    name="Joke_Improver",
    model_client=model_client,
    system_message=(
        "Improve a joke by adding clever wordplay. A seasoned writer who polishes jokes for punch."
    ),
)

joke_polisher = AssistantAgent(
    name="Joke_Polisher",
    model_client=model_client,
    system_message=(
        "Add a surprising twist to a joke. A storyteller who knows how to twist endings for effect."
    ),
)

# -- Teams (one per sub-crew) --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team_gen = RoundRobinGroupChat(
    participants=[joke_generator],
    termination_condition=termination,
)

# -- Team for improver (defined for completeness) --
max_msg_termination_imp = MaxMessageTermination(10)
termination_imp = max_msg_termination_imp

team_improver = RoundRobinGroupChat(
    participants=[joke_improver],
    termination_condition=termination_imp,
)

# -- Team for polisher (defined for completeness) --
max_msg_termination_pol = MaxMessageTermination(10)
termination_pol = max_msg_termination_pol

team_polisher = RoundRobinGroupChat(
    participants=[joke_polisher],
    termination_condition=termination_pol,
)


async def main():
    # Representative concrete input as in the original crewai example:
    topic = "cats"

    task_text = f"Write a short joke about {topic}."

    # Run the generator team and stream output, collecting the assistant text.
    stream = team_gen.run_stream(task=task_text)

    collected: List[str] = []
    try:
        async for event in stream:
            # Robust extraction of textual payloads from different event shapes.
            text_piece = ""
            try:
                if isinstance(event, dict):
                    text_piece = (
                        event.get("content")
                        or event.get("message")
                        or event.get("text")
                        or str(event)
                    )
                else:
                    text_piece = getattr(event, "content", None) or getattr(
                        event, "text", None
                    ) or str(event)
            except Exception:
                text_piece = str(event)
            # Print streaming output as it arrives.
            print(text_piece, end="", flush=True)
            collected.append(text_piece)
    except TypeError:
        # If stream is not async-iterable, fall back to Console for compatibility.
        await Console(stream)

    final_joke = "".join(collected).strip()

    print("\n\n--- Result ---")
    if final_joke:
        print(final_joke)
    else:
        print("(no text captured from model stream)")

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
