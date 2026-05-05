#!/usr/bin/env python
from crewai.flow.flow import Flow, listen, router, start

from crews.hiring_crew import HiringCrew


class HiringPipeline(Flow):

    @start()
    def receive_application(self):
        result = HiringCrew().crew().kickoff(
            inputs={"position": "Senior Software Engineer"}
        )
        self.state["screening_result"] = result
        return result

    @router(receive_application)
    def evaluate_screening(self):
        score = self.state.get("screening_score", 5)
        if score >= 7:
            return "proceed_to_interview"
        else:
            return "reject_candidate"

    @listen("proceed_to_interview")
    def conduct_interviews(self):
        result = HiringCrew().crew().kickoff(
            inputs={"position": "Senior Software Engineer"}
        )
        return result

    @listen("reject_candidate")
    def send_rejection(self):
        print("Candidate does not meet minimum requirements.")

    @listen(conduct_interviews)
    def finalize_decision(self):
        print("Final decision made.")


if __name__ == "__main__":
    flow = HiringPipeline()
    flow.kickoff()
