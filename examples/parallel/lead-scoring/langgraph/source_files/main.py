"""
lead-scoring — LangGraph port of the CrewAI original.

Original: examples/parallel/lead-scoring/crewai — a CrewAI Flow over two
sub-crews (LeadScoreCrew / hr_evaluation_agent and LeadResponseCrew /
email_followup_agent) with a @router human-in-the-loop gate.

LangGraph mapping:
  - CrewAI Flow            -> a StateGraph:
        load_leads -> hr_evaluation_agent -> human_in_the_loop
                   -> (loop back to scoring | email_followup_agent)
  - LeadScoreCrew agent    -> hr_evaluation_agent node (LLM scores leads).
  - LeadResponseCrew agent -> email_followup_agent node (LLM writes emails).
  - @router human_in_the_loop -> conditional edge driven by human input().
"""

import csv
import operator
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

load_dotenv()


class LeadScoreState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    candidates: list
    candidate_scores: list
    scored_leads_feedback: str
    emails: list


def load_leads(state: LeadScoreState):
    with open("leads.csv", newline="", encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))
    return {"candidates": candidates}


def hr_evaluation_agent(state: LeadScoreState):
    llm = ChatOpenAI(model="gpt-4o")
    system_prompt = SystemMessage(
        content=(
            "You are a Senior HR Evaluation Expert. Analyze candidates' "
            "qualifications and compare them against the job description to "
            "provide a score (1-100) and reasoning."
        )
    )
    scores = []
    for c in state["candidates"]:
        prompt = (
            f"Evaluate this candidate against the job and give a score and reason. "
            f"Candidate: {c}. Feedback: {state.get('scored_leads_feedback', '')}"
        )
        resp = llm.invoke([system_prompt, HumanMessage(content=prompt)])
        scores.append(resp.content)
    return {"candidate_scores": scores}


def human_in_the_loop(state: LeadScoreState):
    print("Top candidates ready for review.")
    print("1. Redo lead scoring with feedback")
    print("2. Proceed with writing emails")
    choice = input("Enter the number of your choice: ")
    if choice == "1":
        feedback = input("Provide additional feedback: ")
        return {"scored_leads_feedback": feedback}
    return {}


def should_continue(state: LeadScoreState):
    if state.get("scored_leads_feedback"):
        return "score"
    return "email"


def email_followup_agent(state: LeadScoreState):
    llm = ChatOpenAI(model="gpt-4o")
    system_prompt = SystemMessage(
        content=(
            "You are an HR Coordinator named Sarah. Compose personalized "
            "follow-up emails to candidates based on their bio and whether they "
            "are being pursued. If proceeding, request availability for a Zoom "
            "call; otherwise send a polite rejection."
        )
    )
    emails = []
    for c, score in zip(state["candidates"], state["candidate_scores"]):
        prompt = f"Write a follow-up email for candidate {c} given the evaluation: {score}"
        resp = llm.invoke([system_prompt, HumanMessage(content=prompt)])
        emails.append(resp.content)
    return {"emails": emails}


graph = StateGraph(LeadScoreState)
graph.add_node("load_leads", load_leads)
graph.add_node("hr_evaluation_agent", hr_evaluation_agent)
graph.add_node("human_in_the_loop", human_in_the_loop)
graph.add_node("email_followup_agent", email_followup_agent)

graph.set_entry_point("load_leads")
graph.add_edge("load_leads", "hr_evaluation_agent")
graph.add_edge("hr_evaluation_agent", "human_in_the_loop")
graph.add_conditional_edges(
    "human_in_the_loop",
    should_continue,
    {"score": "hr_evaluation_agent", "email": "email_followup_agent"},
)
graph.add_edge("email_followup_agent", END)

app = graph.compile()


def run():
    print("Starting LangGraph Lead Scoring...")
    result = app.invoke(
        {"messages": [], "candidates": [], "candidate_scores": [], "scored_leads_feedback": "", "emails": []}
    )
    print("Completed!")
    for email in result["emails"]:
        print(email)


if __name__ == "__main__":
    run()
