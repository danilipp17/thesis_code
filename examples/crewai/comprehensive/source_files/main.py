from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen, router
from crews.comprehensive_crew import ComprehensiveCrew


# Triggers 'agentoscin:Schema' mapping on Flow State
class OrchestratorState(BaseModel):
    topic: str = ""
    approved: bool = False


# Triggers 'agentoscin:Orchestration'
class MasterOrchestratorFlow(Flow[OrchestratorState]):
    @start()  # Triggers 'agentoscin:StartStep'
    def initialize_system(self):
        return "init_done"

    @router(
        initialize_system
    )  # Triggers 'agentoscin:RoutingTermination' (ConditionalStep)
    def verification_router(self):
        if self.state.topic:
            return "execute_crew"
        return "halt_system"

    @listen("execute_crew")  # Triggers 'agentoscin:WorkflowStep'
    def run_crew_pipeline(self):
        crew = ComprehensiveCrew()
        result = crew.crew().kickoff(inputs={"topic": self.state.topic})
        return result

    @listen("halt_system")  # Triggers 'agentoscin:EndStep'
    def terminate(self):
        return "Flow Terminated."
