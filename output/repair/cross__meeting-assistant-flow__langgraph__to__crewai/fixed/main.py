"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional
import os
import csv
import json
import re

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
        """
        Read meeting transcript from `meeting_notes.txt` if present,
        otherwise set a short default transcript. Store it on self.state.
        """
        path = "meeting_notes.txt"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"[load_meeting_notes] Loaded transcript from {path} ({len(content)} chars)")
        else:
            # Small default input so the flow can run even if no file is provided.
            # This is allowed as "input" — the model will still generate the tasks.
            content = (
                "Team kickoff meeting. Discussed timeline for Project Alpha, "
                "assigned Alice to research vendor options, Bob to prepare the budget draft, "
                "and Carol to draft initial requirements. Follow-up meeting in two weeks."
            )
            print("[load_meeting_notes] No meeting_notes.txt found; using a default transcript.")
        # store on flow state
        self.state.transcript = content

    @listen(load_meeting_notes)
    def analyze_meeting(self):
        """
        Call an LLM to extract actionable tasks from the transcript.
        The model is asked to return a JSON list of {"name": str, "description": str} objects.
        The parsed list is stored on self.state.tasks.
        """
        prompt = (
            "You are an expert in analyzing meeting transcripts and summarizing "
            "the discussions into actionable tasks. Analyze the provided meeting "
            "transcript and generate a JSON list of objects with keys "
            '"name" and "description".\n\n'
            f"Transcript:\n{self.state.transcript}\n\n"
            "Return ONLY valid JSON: a top-level JSON array of objects like "
            '[{"name": "Task name", "description": "Longer description"}, ...]'
        )

        # Try to use langchain_openai.ChatOpenAI if available, else fall back to openai package.
        response_text = None
        try:
            # Preferred: langchain_openai wrapper used in the original reference.
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"))
            # ChatOpenAI.invoke may return an object with .content
            resp = llm.invoke(prompt)
            # Try a couple of possible attributes
            if hasattr(resp, "content"):
                response_text = resp.content
            elif hasattr(resp, "text"):
                response_text = resp.text
            else:
                # Fallback to stringification
                response_text = str(resp)
        except Exception:
            # Fallback to openai.ChatCompletion if langchain_openai is not available.
            try:
                import openai
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if openai_api_key:
                    openai.api_key = openai_api_key
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
                # Use ChatCompletions API
                completion = openai.ChatCompletion.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                )
                # Extract text
                response_text = completion.choices[0].message.get("content", "")
            except Exception as e:
                # If we cannot call a remote model for any reason, re-raise so failure is visible.
                raise RuntimeError(f"Failed to call an LLM: {e}")

        # Ensure we have some text
        if not response_text:
            raise RuntimeError("LLM returned empty response")

        # Attempt to parse JSON from the model output robustly.
        tasks = []
        try:
            tasks = json.loads(response_text)
            if not isinstance(tasks, list):
                raise ValueError("Parsed JSON is not a list")
        except Exception:
            # Try to extract JSON block from response_text using a regex.
            m = re.search(r"(\[.*\])", response_text, re.S)
            if m:
                try:
                    tasks = json.loads(m.group(1))
                except Exception:
                    tasks = []
            else:
                tasks = []

        # Normalize each task to dict with name/description keys
        normalized = []
        for t in tasks:
            if isinstance(t, dict):
                name = t.get("name") if t.get("name") is not None else str(t.get("title", ""))
                desc = t.get("description", "") if t.get("description") is not None else ""
                normalized.append({"name": name, "description": desc})
        self.state.tasks = normalized
        print(f"[analyze_meeting] Extracted {len(self.state.tasks)} tasks from transcript.")

    @listen(analyze_meeting)
    def upload_trello(self):
        """
        Simulate uploading tasks to Trello by printing each task in Trello format.
        This mirrors the side-effect helper in the LangGraph reference.
        """
        for t in self.state.tasks:
            name = t.get("name", "")
            desc = t.get("description", "")
            print(f"[Trello] {name}: {desc}")

    @listen(upload_trello)
    def save_csv(self):
        """
        Save tasks to new_tasks.csv in the current directory.
        """
        path = "new_tasks.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Name", "Description"])
            for t in self.state.tasks:
                w.writerow([t.get("name", ""), t.get("description", "")])
        print(f"[save_csv] Wrote {len(self.state.tasks)} tasks to {path}")

    @listen(save_csv)
    def notify_slack(self):
        """
        Simulate sending a Slack notification by printing a message.
        """
        msg = f"{len(self.state.tasks)} New tasks have been added to Trello!"
        print(f"[Slack] {msg}")


def kickoff():
    flow = StateGraph()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
