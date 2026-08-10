"""
Auto-generated CrewAI Flow: AutoGenFlow

This module was repaired to provide a working start step that reads a
meeting transcript (if present), extracts simple actionable tasks using
deterministic heuristics, prints the resulting JSON tasks, writes a CSV,
and calls the stubbed tools for side-effects.
"""

import dotenv
import os
import re
import json
import csv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

# Keep the same dotenv usage as generated
dotenv.load_dotenv()

# Import the top-level tools functions (the generated package contains
# tool classes, but we provide the original helper functions in
# tools.__init__.py so this import stays valid).
from tools import save_tasks_to_trello, send_message_to_channel


class AutoGenFlowState(BaseModel):
    """Flow state — customize fields as needed."""
    # No persistent state required for this simple repaired flow.
    pass


class AutoGenFlow(Flow[AutoGenFlowState]):
    @start()
    def run_team(self):
        """
        Replacement implementation for the generated start step.

        Behavior:
          - Read `meeting_notes.txt` if present, otherwise use a default
            sample transcript.
          - Extract actionable items using simple deterministic rules.
          - Print the JSON list of tasks.
          - Write new_tasks.csv and call the two tool helpers for side effects.
        """
        # Attempt to load a transcript from file; fallback to a sample.
        transcript_path = "meeting_notes.txt"
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = f.read()
        else:
            transcript = (
                "Project kickoff completed. Action: Alice to draft initial project plan by next Tuesday.\n"
                "We need to finalize the budget — Bob will follow up with finance.\n"
                "Discussed UI changes; TODO: Carol to produce mockups.\n"
                "Set up recurring sync meetings every Monday."
            )

        # Deterministic heuristic task extraction:
        # - Split into candidate sentences/lines
        # - Look for keywords indicating actions
        candidates = re.split(r'[\n\.]+', transcript)
        keywords = re.compile(
            r'\b(action|actions|todo|we need to|follow up|follow-up|assign|assign to|will)\b',
            flags=re.IGNORECASE,
        )

        tasks: List[Dict[str, str]] = []
        for c in candidates:
            s = c.strip()
            if not s:
                continue
            if keywords.search(s):
                # Make a short name and a fuller description
                words = s.split()
                name = " ".join(words[:6])
                if len(name) > 60:
                    name = name[:57].rstrip() + "..."
                description = s
                tasks.append({"name": name, "description": description})

        # If no tasks found, produce two conservative default tasks
        if not tasks:
            tasks = [
                {
                    "name": "Draft summary of meeting",
                    "description": "Create a concise summary of the meeting and circulate to attendees.",
                },
                {
                    "name": "Identify next steps",
                    "description": "List concrete next steps, owners, and due dates based on the discussion.",
                },
            ]

        # Print the resulting JSON (primary requested output)
        tasks_json = json.dumps(tasks, indent=2, ensure_ascii=False)
        print(tasks_json)

        # Persist to CSV like the original reference implementation
        csv_path = "new_tasks.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Name", "Description"])
            for t in tasks:
                w.writerow([t.get("name", ""), t.get("description", "")])

        # Call the stubbed tools for side-effects (these print to stdout).
        try:
            save_tasks_to_trello(tasks)
        except Exception as e:
            print(f"[tools.save_tasks_to_trello] Error: {e}")

        try:
            send_message_to_channel(f"{len(tasks)} New tasks have been added to Trello!")
        except Exception as e:
            print(f"[tools.send_message_to_channel] Error: {e}")


def kickoff():
    flow = AutoGenFlow()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
