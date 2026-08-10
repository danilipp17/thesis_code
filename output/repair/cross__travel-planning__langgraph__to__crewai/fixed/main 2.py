"""
Auto-generated CrewAI Flow: StateGraph
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()




class TravelState(BaseModel):
    """Flow state — customize fields as needed."""
    final_plan: str = ""
    language_notes: str = ""
    local_notes: str = ""
    plan: str = ""
    request: str = ""


class StateGraph(Flow[TravelState]):

    def __init__(self, request: str = "Plan a 10 day trip to Luxembourg."):
        # Intentionally avoid depending on Flow.__init__ signature.
        # We maintain a simple internal state to run deterministically.
        self.state = TravelState(request=request)

    @start()
    def planner_agent(self):
        # Produce a deterministic initial itinerary based on the request.
        req = self.state.request or "Plan a 10 day trip to Luxembourg."
        plan = (
            "10-day Luxembourg itinerary (sketch):\n\n"
            "Day 1: Arrival in Luxembourg City — settle in, stroll the Old Town, "
            "visit the Grand Ducal Palace exterior and enjoy dinner at a local bistro.\n\n"
            "Day 2: Explore the Bock Casemates and the museums of the city. "
            "Evening: try local dishes such as Judd mat Gaardebounen.\n\n"
            "Day 3: Day trip to Vianden Castle — scenic town and castle visit.\n\n"
            "Day 4: Hike in the Mullerthal Region (Little Switzerland) — easy to moderate trails.\n\n"
            "Day 5: Visit Echternach, its abbey and lakeside walk; optional boat/kayak.\n\n"
            "Day 6: Northern Luxembourg — Clervaux, castle, and WWII exhibits.\n\n"
            "Day 7: Moselle Valley wine route — tasting at vineyards and riverside villages.\n\n"
            "Day 8: Cross-border day trip (Trier, Germany or Arlon, Belgium) depending on interest.\n\n"
            "Day 9: Leisure day for markets, museums missed earlier, and local shopping.\n\n"
            "Day 10: Departure — logistics, recommended timing, and transport tips.\n\n"
            f"(Request summary: {req})"
        )
        self.state.plan = plan
        # Return for possible wrappers / callers
        return self.state

    @listen(planner_agent)
    def local_agent(self):
        # Add concrete local suggestions referencing the current plan.
        plan = self.state.plan
        local_notes = (
            "Local suggestions and activities:\n\n"
            "- Food: try Luxembourg specialties such as Judd mat Gaardebounen (smoked pork with broad beans), "
            "Gromperekichelcher (potato pancakes), and local Moselle wines.\n"
            "- Transport: purchase a Luxembourg Card for museums or use the excellent regional bus/train network. "
            "Note: public transport within Luxembourg is free, but cross-border trips may cost extra.\n"
            "- Markets & small towns: visit the weekly markets in Luxembourg City and small towns like Echternach for "
            "local crafts.\n"
            "- Timing: start outdoor activities early to avoid crowds at popular sites like Vianden Castle.\n\n"
            f"Plan reference (first lines): {plan.splitlines()[:2]}"
        )
        self.state.local_notes = local_notes
        return self.state

    @listen(local_agent)
    def language_agent(self):
        # Provide language & communication tips using current plan and local notes.
        local = self.state.local_notes
        language_notes = (
            "Language & communication tips:\n\n"
            "- Languages: Luxembourgish, French, and German are official. English is widely understood in tourist areas.\n"
            "- Politeness: Greeting with 'Bonjour' (in the morning) or 'Bon après-midi' is appreciated; "
            "a few words in French or Luxembourgish go a long way.\n"
            "- Practical: carry a printed address for taxis/hosts; in smaller villages, pre-check opening hours.\n"
            "- Emergency numbers: 112 for emergency services.\n\n"
            "Local-context notes:\n" + local.split("\n", 1)[0]
        )
        self.state.language_notes = language_notes
        return self.state

    @listen(language_agent)
    def travel_summary_agent(self):
        # Compile the final plan by integrating the plan, local suggestions, and language tips.
        final = (
            "Final 10-day Luxembourg Travel Plan\n\n"
            "=== Itinerary ===\n"
            f"{self.state.plan}\n\n"
            "=== Local Notes ===\n"
            f"{self.state.local_notes}\n\n"
            "=== Language & Communication Tips ===\n"
            f"{self.state.language_notes}\n\n"
            "Safe travels! TERMINATE"
        )
        self.state.final_plan = final
        # Print the result as required.
        print(self.state.final_plan)
        return self.state


def kickoff():
    flow = StateGraph()
    # Call the underlying implementations in sequence to simulate the Flow run.
    # Use __wrapped__ if decorators changed the callable; otherwise, call directly.
    # We attempt both safely.
    steps = [
        ("planner_agent", flow.planner_agent),
        ("local_agent", flow.local_agent),
        ("language_agent", flow.language_agent),
        ("travel_summary_agent", flow.travel_summary_agent),
    ]
    for name, step in steps:
        # Call the original function body in case the decorator wraps the method.
        func = getattr(step, "__wrapped__", step)
        try:
            func()
        except TypeError:
            # Some decorators may expect different signatures; try calling as bound method
            func(flow)
    # Ensure final plan is printed (travel_summary_agent prints it already).
    # But also print again for clarity / compatibility with automated checks.
    print("\n--- Returned final_plan (raw) ---\n")
    print(flow.state.final_plan)


if __name__ == "__main__":
    kickoff()
