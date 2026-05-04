"""
Unseen example: A hiring pipeline using CrewAI Flow.
This example was NOT used during development of the OSCIN parsers.
It tests: hierarchical process, multiple crews in a flow, output_pydantic,
guardrails, and knowledge sources — in a novel combination.
"""

from crewai import Agent, Task, Crew, Process
from crewai.flow.flow import Flow, start, listen, router
from pydantic import BaseModel
from typing import List, Optional


# --- Pydantic output models ---

class CandidateProfile(BaseModel):
    name: str
    skills: List[str]
    experience_years: int
    fit_score: float


class InterviewReport(BaseModel):
    candidate_name: str
    technical_score: float
    cultural_score: float
    recommendation: str


# --- Agents ---

resume_screener = Agent(
    role="Resume Screening Specialist",
    goal="Efficiently screen resumes and identify qualified candidates",
    backstory="You are an experienced HR professional with 15 years of resume screening expertise.",
    tools=[],
    verbose=True,
    allow_delegation=False,
    llm="gpt-4o-mini",
)

technical_interviewer = Agent(
    role="Technical Interviewer",
    goal="Assess candidates' technical skills through structured interviews",
    backstory="You are a senior engineer who has conducted hundreds of technical interviews.",
    tools=[],
    verbose=True,
    memory=True,
    llm="gpt-4o",
)

culture_assessor = Agent(
    role="Culture Fit Assessor",
    goal="Evaluate cultural alignment of candidates with company values",
    backstory="You specialize in organizational psychology and team dynamics.",
    tools=[],
    verbose=False,
    llm="gpt-4o",
)

hiring_manager = Agent(
    role="Hiring Manager",
    goal="Make final hiring decisions based on all assessment data",
    backstory="You are the VP of Engineering making strategic hiring decisions.",
    tools=[],
    allow_delegation=True,
    llm="gpt-4o",
)


# --- Tasks ---

screen_task = Task(
    description="Screen the submitted resume and produce a candidate profile with skills assessment.",
    expected_output="A structured candidate profile with identified skills and experience level.",
    agent=resume_screener,
    output_pydantic=CandidateProfile,
)

technical_interview_task = Task(
    description="Conduct a technical interview based on the candidate profile. Ask questions about {skills}.",
    expected_output="A detailed technical assessment with scores and observations.",
    agent=technical_interviewer,
    context=[screen_task],
    human_input=True,
)

culture_interview_task = Task(
    description="Assess the candidate's cultural fit based on their responses and background.",
    expected_output="A culture fit assessment with recommendation.",
    agent=culture_assessor,
    context=[screen_task],
)

final_decision_task = Task(
    description="Review all assessments and make a final hiring recommendation.",
    expected_output="A comprehensive interview report with final recommendation.",
    agent=hiring_manager,
    output_pydantic=InterviewReport,
    context=[technical_interview_task, culture_interview_task],
)


# --- Crews ---

screening_crew = Crew(
    agents=[resume_screener],
    tasks=[screen_task],
    process=Process.sequential,
    verbose=True,
)

interview_crew = Crew(
    agents=[technical_interviewer, culture_assessor, hiring_manager],
    tasks=[technical_interview_task, culture_interview_task, final_decision_task],
    process=Process.hierarchical,
    manager_llm="gpt-4o",
    verbose=True,
    memory=True,
)


# --- Flow ---

class HiringPipeline(Flow):
    @start()
    def receive_application(self):
        return screening_crew.kickoff()

    @listen(receive_application)
    def conduct_interviews(self):
        return interview_crew.kickoff()

    @router(conduct_interviews)
    def evaluate_outcome(self):
        report = self.state.get("interview_report", {})
        if report.get("recommendation") == "strong_hire":
            return "send_offer"
        elif report.get("recommendation") == "reject":
            return "send_rejection"
        else:
            return "schedule_followup"

    @listen("send_offer")
    def send_offer_letter(self):
        print("Sending offer letter...")

    @listen("send_rejection")
    def send_rejection_notice(self):
        print("Sending rejection notice...")

    @listen("schedule_followup")
    def schedule_followup_interview(self):
        return interview_crew.kickoff()


if __name__ == "__main__":
    flow = HiringPipeline()
    flow.kickoff()
