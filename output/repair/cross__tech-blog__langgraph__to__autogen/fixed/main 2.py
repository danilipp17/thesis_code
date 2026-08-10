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
        "You are a researcher agent. When given a user prompt containing a topic, "
        "provide a comprehensive research summary of that topic. Respond with the research content "
        "only, and prefix your output with the marker: RESEARCH:\n\n"
        "Example:\nRESEARCH: <your research text here>"
    ),
)

writer = AssistantAgent(
    name="writer",
    model_client=model_client,
    system_message=(
        "You are a writer agent. You will receive research content prefixed with 'RESEARCH:'. "
        "Using that research, write a ~500-word engaging tech blog post. Respond with the draft only, "
        "and prefix your output with the marker: DRAFT:\n\n"
        "Example:\nDRAFT: <your draft here>"
    ),
)

editor = AssistantAgent(
    name="editor",
    model_client=model_client,
    system_message=(
        "You are an editor agent. You will receive a draft prefixed with 'DRAFT:'. "
        "Review the draft, fix grammatical errors, improve flow, and return the final polished version "
        "ready for publishing. Prefix your output with the marker: FINAL_POST:\n\n"
        "Example:\nFINAL_POST: <final post here>"
    ),
)

# -- Team --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[researcher, writer, editor],
    termination_condition=termination,
)


async def main():
    # Concrete input (wired in instead of a literal placeholder)
    topic = "Agentic AI Frameworks"

    # Provide the user/task message that starts the workflow with the concrete topic.
    task = f"Research the following topic and provide a comprehensive summary: {topic}"

    # Run the team as a stream so we can print progress and capture the final post.
    stream = team.run_stream(task=task)

    final_output: Optional[str] = None
    # Consume stream; print human-readable messages as they arrive and capture final post.
    async for msg in stream:
        # Attempt to extract content robustly from different possible message shapes.
        content = None
        try:
            # common attribute used by many message implementations
            content = getattr(msg, "content", None)
        except Exception:
            content = None

        if content is None:
            # fallback checks
            if isinstance(msg, dict):
                content = msg.get("content") or msg.get("text") or msg.get("message")
            else:
                # final fallback to string representation
                try:
                    content = str(msg)
                except Exception:
                    content = None

        # Print the content (or the repr of the message) so the run is visible
        print(content if content is not None else repr(msg))

        # Try to detect the sender/agent name to know when editor produced output.
        sender = None
        for attr in ("sender_name", "role", "author", "name", "participant", "agent"):
            try:
                sender = getattr(msg, attr)
            except Exception:
                sender = None
            if sender:
                break
        if not sender and isinstance(msg, dict):
            sender = msg.get("sender") or msg.get("role") or msg.get("name")

        # Normalize content to string for marker detection
        cont_str = (content or "")
        if "FINAL_POST:" in cont_str:
            # strip the marker and whitespace
            final_output = cont_str.split("FINAL_POST:", 1)[1].strip()
        else:
            # In case the editor omitted the marker but sender indicates editor, capture that as final.
            if sender and "editor" in str(sender).lower():
                final_output = cont_str.strip()

    print("Completed!")
    print("Final post:")
    if final_output:
        print(final_output)
    else:
        print("(No final post was produced.)")

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
