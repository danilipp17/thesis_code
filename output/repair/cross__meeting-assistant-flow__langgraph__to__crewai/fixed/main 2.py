"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional
import os
import csv
import json

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class MeetingState(BaseModel):
    """Flow state — customize fields as needed."""
    tasks: list[dict] = []
    transcript: str = ""


class StateGraph(Flow[MeetingState]):

    @start()
    def load_meeting_notes(self):
        """Read the meeting transcript from disk (fallback to a default)."""
        transcript_path = "meeting_notes.txt"
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcript = f.read()
                print(f"[load_meeting_notes] Loaded transcript from {transcript_path}")
            except Exception as e:
                transcript = ""
                print(f"[load_meeting_notes] Failed to read {transcript_path}: {e}")
        else:
            # Fallback sample transcript so the flow can run end-to-end.
            transcript = (
                "Project sync meeting:\n"
                "- Action: Alice to prepare Q2 roadmap by next Monday.\n"
                "- TODO: Review the design proposal and provide feedback.\n"
                "We also discussed the deployment schedule and risk mitigation.\n"
                "Next meeting scheduled for Friday."
            )
            print("[load_meeting_notes] meeting_notes.txt not found — using default transcript")

        # Assign into the flow state
        try:
            self.state.transcript = transcript
        except Exception:
            # In case the Flow uses a different state container
            setattr(self, "state", MeetingState(transcript=transcript, tasks=[]))

    @listen(load_meeting_notes)
    def analyze_meeting(self):
        """Extract actionable tasks from the transcript using a simple heuristic."""
        try:
            transcript = self.state.transcript
        except Exception:
            transcript = getattr(self, "state", MeetingState()).transcript

        tasks: List[Dict[str, str]] = []
        for line in transcript.splitlines():
            s = line.strip()
            if not s:
                continue
            # Heuristic for action items
            if s.lower().startswith("action:") or s.lower().startswith("- action") or "todo" in s.lower() or s.lower().startswith("- "):
                name = s
                # Shorten name for brevity
                if len(name) > 80:
                    name = name[:77] + "..."
                tasks.append({"name": name, "description": s})
        if not tasks:
            # If none found, create a single summary task
            summary = transcript.strip()
            if len(summary) > 200:
                summary = summary[:197] + "..."
            tasks.append({"name": "Summarize meeting and extract tasks", "description": summary})

        # Assign into state
        try:
            self.state.tasks = tasks
        except Exception:
            setattr(self, "state", MeetingState(transcript=transcript, tasks=tasks))

        print(f"[analyze_meeting] Extracted {len(tasks)} task(s)")

    @listen(analyze_meeting)
    def upload_trello(self):
        """Stub: print Trello-side effects for each task."""
        try:
            tasks = self.state.tasks
        except Exception:
            tasks = getattr(self, "state", MeetingState()).tasks

        for t in tasks:
            print(f"[Trello] {t.get('name', '')}: {t.get('description', '')}")

        print("[upload_trello] Completed uploading tasks to Trello (stub)")

    @listen(upload_trello)
    def save_csv(self):
        """Save tasks to new_tasks.csv"""
        try:
            tasks = self.state.tasks
        except Exception:
            tasks = getattr(self, "state", MeetingState()).tasks

        filename = "new_tasks.csv"
        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Name", "Description"])
                for t in tasks:
                    w.writerow([t.get("name", ""), t.get("description", "")])
            print(f"[save_csv] Wrote {len(tasks)} tasks to {filename}")
        except Exception as e:
            print(f"[save_csv] Failed to write {filename}: {e}")

    @listen(save_csv)
    def notify_slack(self):
        """Stub: print Slack notification."""
        try:
            tasks = self.state.tasks
        except Exception:
            tasks = getattr(self, "state", MeetingState()).tasks

        msg = f"{len(tasks)} New tasks have been added to Trello!"
        print(f"[Slack] {msg}")
        print("[notify_slack] Notification sent (stub)")


def kickoff():
    flow = StateGraph()
    # Run the flow
    try:
        flow.kickoff()
    except Exception as e:
        # Ensure we still surface useful debug if the framework differs
        print(f"[kickoff] Flow kickoff raised an exception: {e}")

    # Print final state for visibility
    final_state = None
    try:
        final_state = flow.state
        if isinstance(final_state, MeetingState):
            print("[kickoff] Final state:", final_state.json(indent=2))
        else:
            # pydantic BaseModel may serialize differently; fallback to dict
            print("[kickoff] Final state (repr):", repr(final_state))
    except Exception:
        try:
            # Attempt flexible access
            s = getattr(flow, "state", None)
            if s is None:
                print("[kickoff] No final state available on flow")
            else:
                try:
                    print("[kickoff] Final state:", json.dumps(s.__dict__, indent=2))
                except Exception:
                    print("[kickoff] Final state (raw):", s)
        except Exception as e:
            print(f"[kickoff] Failed to print final state: {e}")


if __name__ == "__main__":
    kickoff()
