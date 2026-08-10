"""
Auto-generated CrewAI Flow: MeetingFlow
"""

import dotenv
import os
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel, Field

dotenv.load_dotenv()

from crews.meeting_assistant_crew.meeting_assistant_crew import MeetingAssistantCrew
from models import MeetingTask


class MeetingState(BaseModel):
    """Flow state — customize fields as needed."""
    tasks: List[MeetingTask] = Field(default_factory=list)
    transcript: str = "Meeting transcript goes here"

class MeetingFlow(Flow[MeetingState]):
    initial_state = MeetingState

    @start()
    def load_meeting_notes(self):
        print("Loading Meeting Notes")
        print("Current working directory:", os.getcwd())
        # Try to read meeting_notes.txt if present, otherwise keep default transcript.
        if os.path.exists("meeting_notes.txt"):
            with open("meeting_notes.txt", "r") as file:
                self.state.transcript = file.read()
        else:
            print("meeting_notes.txt not found; using default transcript.")

    @listen(load_meeting_notes)
    def generate_tasks_from_meeting_transcript(self):
        print("Kickoff the Meeting Assistant Crew")
        # Kick off the crew with the transcript from state
        output = MeetingAssistantCrew().crew().kickoff(inputs={"transcript": self.state.transcript})

        # Attempt to robustly extract tasks from returned output
        tasks = []
        if isinstance(output, dict):
            if "tasks" in output:
                tasks = output["tasks"]
            elif "analyze_meeting" in output and isinstance(output["analyze_meeting"], dict):
                tasks = output["analyze_meeting"].get("tasks", [])
            else:
                # fallback: if the crew returned a single value that's the task list
                # try to find any list-like entry
                for v in output.values():
                    if isinstance(v, list):
                        tasks = v
                        break
        else:
            # If output is a list (e.g., direct tasks), accept it
            if isinstance(output, list):
                tasks = output

        print("TASKS:", tasks)
        # Assign to state; keep as-is (assuming items conform to MeetingTask)
        self.state.tasks = tasks

    @listen(generate_tasks_from_meeting_transcript)
    def add_tasks_to_trello(self):
        print("Adding Tasks to Trello (skipped in this demo).")
        # In a full integration you would call your Trello helper here.

    @listen(generate_tasks_from_meeting_transcript)
    def save_new_tasks_to_csv(self):
        print("Saving New Tasks to CSV (skipped in this demo).")
        # In a full integration you would write tasks to CSV here.

    @listen(generate_tasks_from_meeting_transcript)
    def send_slack_notification(self):
        print("Sending Slack Notification (skipped in this demo).")
        # In a full integration you would send a Slack message here.

def kickoff():
    flow = MeetingFlow()
    flow.kickoff()

if __name__ == "__main__":
    kickoff()
