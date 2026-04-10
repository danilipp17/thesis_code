from dotenv import load_dotenv
load_dotenv()
from crewai.flow.flow import Flow, start, listen, router
from crews.research_crew.research_crew import AcademicResearchCrew
from pydantic import BaseModel

class AcademicState(BaseModel):
    topic: str = ""
    paper: str = ""
    status: str = ""

class AcademicResearchFlow(Flow[AcademicState]):

    @start()
    def initialize_research(self):
        print(f"Starting research for topic: {self.state.topic}")
        # Setup stuff
        
    @listen(initialize_research)
    def conduct_research(self):
        print("Crew is taking over...")
        result = AcademicResearchCrew().crew().kickoff(inputs={"topic": self.state.topic})
        self.state.paper = str(result)
        self.state.status = "SUCCESS" if result else "FAILED"
        return self.state.status

    @router(conduct_research)
    def review_outcome(self):
        if self.state.status == "SUCCESS":
            return "publish_paper"
        elif self.state.status == "FAILED":
            return "abort_research"

    @listen("publish_paper")
    def publish_paper(self):
        print("Paper published successfully.")

    @listen("abort_research")
    def abort_research(self):
        print("Research aborted.")

if __name__ == "__main__":
    flow = AcademicResearchFlow()
    flow.kickoff(inputs={"topic": "The economic impact of artificial intelligence in software engineering"})
