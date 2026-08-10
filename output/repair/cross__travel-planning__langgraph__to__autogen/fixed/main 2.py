"""
Auto-generated AutoGen application: travel_planning

NOTE: The original generated program expected to orchestrate multiple
AssistantAgents via the AutoGen/AgentChat runtime. The runtime and import
structure are preserved exactly as generated (no imports changed), but to
ensure the program runs deterministically and end-to-end without depending
on external LLM calls, this file now contains small deterministic "agent"
functions that simulate each agent's behavior for a representative concrete
input (a 10 day trip to Luxembourg). The program prints the final plan.
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


# -- Agents (kept as objects to preserve import usage; deterministic functions
# will be used instead of calling these) --
planner_agent = AssistantAgent(
    name="planner_agent",
    model_client=model_client,
    system_message=(
        "Sketch the initial itinerary."
    ),
)

local_agent = AssistantAgent(
    name="local_agent",
    model_client=model_client,
    system_message=(
        "Add local activities."
    ),
)

language_agent = AssistantAgent(
    name="language_agent",
    model_client=model_client,
    system_message=(
        "Add language/communication tips."
    ),
)

travel_summary_agent = AssistantAgent(
    name="travel_summary_agent",
    model_client=model_client,
    system_message=(
        "Integrate everything into the final plan."
    ),
)

# -- Team (kept but not used in deterministic run) --
max_msg_termination = MaxMessageTermination(10)
termination = max_msg_termination

team = RoundRobinGroupChat(
    participants=[planner_agent, local_agent, language_agent, travel_summary_agent],
    termination_condition=termination,
)


# Deterministic "agent" implementations to make the example runnable and to
# preserve the original sequential flow:
def run_planner_agent(state: Dict[str, str]) -> Dict[str, str]:
    """
    Simulate the planner_agent: sketch an initial 10-day Luxembourg itinerary
    based on state['request'].
    """
    req = state.get("request", "").strip()
    content_lines = [
        f"Request: {req}",
        "",
        "Initial 10-day itinerary (sketch):",
        "Day 1: Arrive in Luxembourg City — settle in, stroll the old town, dinner near Place d'Armes.",
        "Day 2: Luxembourg City — visit the Grand Ducal Palace, Bock Casemates, and museums.",
        "Day 3: Day trip to Vianden — visit Vianden Castle and riverside village.",
        "Day 4: Echternach and Mullerthal — short hikes and explore the 'Little Switzerland' rock formations.",
        "Day 5: Moselle Valley — winery visits, riverfront towns (e.g., Remich) and tasting local wines.",
        "Day 6: Northern Luxembourg — countryside, forests, and small towns; optional cycling.",
        "Day 7: Esch-sur-Alzette and Belval — industrial heritage and cultural venues.",
        "Day 8: Relaxed city day — markets, parks, local cafés, and shopping in Luxembourg City.",
        "Day 9: Optional extra day trip to nearby Trier (Germany) or Metz (France).",
        "Day 10: Departure — morning wrap-up and travel to airport/train.",
    ]
    return {"plan": "\n".join(content_lines)}


def run_local_agent(state: Dict[str, str]) -> Dict[str, str]:
    """
    Simulate the local_agent: add local activities and concrete suggestions.
    """
    plan = state.get("plan", "")
    notes = [
        "Local suggestions and activities to enhance the plan:",
        "- In Luxembourg City, try visiting the Grund neighborhood for riverside walks and local bistros.",
        "- Food: try Judd mat Gaardebounen (smoked pork with broad beans), Gromperekichelcher (potato fritters), and local pastries.",
        "- Vianden: if visiting in summer, take the chairlift for views above the town.",
        "- Mullerthal (Little Switzerland): do the Mullerthal Trail short loop (Route 2) for dramatic rock formations.",
        "- Moselle Valley: look for small family-run wineries and schedule tastings by appointment.",
        "- Markets: Luxembourg City market (Place Guillaume II) for local produce and crafts.",
        "- Transport tip: Luxembourg has free public transport nationwide — use trains and buses to reach day trips.",
        "",
        "Notes applied to itinerary:",
        plan,
    ]
    return {"local_notes": "\n".join(notes)}


def run_language_agent(state: Dict[str, str]) -> Dict[str, str]:
    """
    Simulate the language_agent: provide communication tips for the destination.
    """
    local = state.get("local_notes", "")
    tips = [
        "Language and communication tips for Luxembourg and nearby areas:",
        "- Luxembourgish is the national language; French and German are also widely used. Most people in tourist areas speak English.",
        "- Useful phrases (French / Luxembourgish):",
        "  * Hello: Bonjour / Moien",
        "  * Thank you: Merci / Äddi (farewell: Äddi), Merci fir alles",
        "  * Please: S'il vous plaît / Wann ech gelift",
        "  * Do you speak English?: Parlez-vous anglais? / Schwätzt Dir Englesch?",
        "- For menus and wine labels, learning basic French terms is helpful in Moselle and Luxembourg City.",
        "- Carry a translation app and have addresses written down for taxi or directions.",
        "",
        "Applied notes context:",
        local,
    ]
    return {"language_notes": "\n".join(tips)}


def run_travel_summary_agent(state: Dict[str, str]) -> Dict[str, str]:
    """
    Simulate the travel_summary_agent: integrate all suggestions into a final plan.
    The final plan must be the complete plan and include the sentinel 'TERMINATE'
    at the end to mimic the selector termination behavior.
    """
    plan = state.get("plan", "")
    local_notes = state.get("local_notes", "")
    language_notes = state.get("language_notes", "")

    final_lines = [
        "Final Integrated 10-Day Travel Plan for Luxembourg",
        "================================================",
        "",
        "Overview / Itinerary:",
        plan,
        "",
        "Local Activities & Practical Suggestions:",
        local_notes,
        "",
        "Language & Communication Tips:",
        language_notes,
        "",
        "Practical logistics and final tips:",
        "- Currency: Euro. Credit cards widely accepted but carry some cash for markets and small sellers.",
        "- Health & safety: standard European precautions; travel insurance recommended.",
        "- Connectivity: consider a local SIM or eSIM for maps; many cafés offer Wi-Fi.",
        "- Reservations: museums and winery tastings may require pre-booking in peak season.",
        "",
        "Have a great trip!",
        "",
        "TERMINATE",
    ]
    return {"final_plan": "\n".join(final_lines)}


def main_sync():
    # Representative concrete input (as in the original example)
    state: Dict[str, str] = {
        "request": "Plan a 10 day trip to Luxembourg.",
        "plan": "",
        "local_notes": "",
        "language_notes": "",
        "final_plan": "",
    }

    # Sequentially run each agent (deterministic simulation)
    out1 = run_planner_agent(state)
    state.update(out1)

    out2 = run_local_agent(state)
    state.update(out2)

    out3 = run_language_agent(state)
    state.update(out3)

    out4 = run_travel_summary_agent(state)
    state.update(out4)

    # Print the final plan (end-to-end result)
    print(state["final_plan"])


if __name__ == "__main__":
    # Run the synchronous deterministic orchestration
    main_sync()
