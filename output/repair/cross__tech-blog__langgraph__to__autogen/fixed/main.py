"""
Auto-generated AutoGen application: tech_blog
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
researcher = AssistantAgent(
    name="researcher",
    model_client=model_client,
    system_message=(
        "You are a researcher. When given a topic, research it and provide a clear, "
        "informative, and comprehensive summary that covers key concepts, recent "
        "developments, and practical implications. Be concise but thorough."
    ),
)

writer = AssistantAgent(
    name="writer",
    model_client=model_client,
    system_message=(
        "You are a writer tasked with producing an engaging, ~500-word tech blog post "
        "based on research material provided. Preserve technical accuracy, explain "
        "concepts clearly for an informed audience, and maintain a friendly, readable tone."
    ),
)

editor = AssistantAgent(
    name="editor",
    model_client=model_client,
    system_message=(
        "You are an editor. Review the provided draft, fix grammatical errors, improve "
        "flow and clarity, and return a polished final post ready for publishing."
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[researcher, writer, editor],
    termination_condition=termination,
)


async def _extract_text_from_event(event: Any) -> (Optional[str], str):
    """
    Attempt to robustly extract a sender name and text content from a streamed event.
    Returns (sender, text)
    """
    sender = None
    text = None

    # Common attribute names to try for sender
    for attr in ("sender", "role", "name", "sender_name", "participant"):
        if hasattr(event, attr):
            try:
                val = getattr(event, attr)
                if isinstance(val, str):
                    sender = val
                else:
                    # If it's e.g. an object with 'name'
                    sender = getattr(val, "name", None) or str(val)
                break
            except Exception:
                continue

    # Common attribute names to try for text/content
    for attr in ("text", "content", "message", "body", "payload"):
        if hasattr(event, attr):
            try:
                val = getattr(event, attr)
                if isinstance(val, str):
                    text = val
                    break
                # sometimes it's an object with .content
                if hasattr(val, "content"):
                    text = getattr(val, "content")
                    break
            except Exception:
                continue

    # Fallback to string representation
    if text is None:
        try:
            text = str(event)
        except Exception:
            text = "<unprintable event>"

    return sender, text


async def main():
    # Concrete topic to be provided to the workflow
    topic = "Agentic AI Frameworks"

    task = f"Research the following topic and provide a comprehensive summary: {topic}"

    # Run the team as a streamed conversation and capture messages.
    stream = team.run_stream(task=task)

    # We'll collect any outputs coming from the 'editor' participant as the final post.
    editor_messages: List[str] = []

    # Iterate through the stream and print messages as they arrive.
    async for event in stream:
        sender, text = await _extract_text_from_event(event)
        # Normalize sender for nicer printing
        sender_label = sender if sender is not None else "unknown"
        print(f"{sender_label}: {text}\n")
        # Capture editor outputs (case-insensitive match)
        try:
            if sender and isinstance(sender, str) and sender.lower() == "editor":
                editor_messages.append(text)
        except Exception:
            pass

    # After stream completes, show final result if available.
    if editor_messages:
        print("Completed!")
        print("Final post (from editor):\n")
        print(editor_messages[-1])
    else:
        print("Completed! No editor output was captured from the run.")

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
