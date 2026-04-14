from crewai.framework import AgenticSystem, LLMAgent, Task, Orchestration, Team

def main():
    # Initialize the Agentic System
    comprehensive_system = AgenticSystem(
        title="ComprehensiveSystem",
        source_framework="CrewAI"
    )

    # Define Language Model
    lm_gpt_4_turbo = comprehensive_system.language_model("gpt-4-turbo")

    # Create Agents
    primary_researcher = LLMAgent(
        id="Primary Researcher",
        role="Primary Researcher",
        type="GeneralPurpose",
        goal="Perform extensive web research.",
        reasoning_enabled=False,
        tool_usage=["web_search"],
        prompt={
            "context": "An expert web researcher.",
            "instruction": "Primary Researcher: Perform extensive web research.",
            "directive_function": "DualDirective",
            "source_attribute": "role, goal, backstory"
        },
        language_model=lm_gpt_4_turbo,
        config={"verbose": "true"},
        knowledge_base="Research_Database",
        private_memory_scope="AgentPrivate"
    )

    senior_analyst = LLMAgent(
        id="Senior Data Analyst",
        role="Senior Data Analyst",
        type="GeneralPurpose",
        goal="Analyze the data provided by the researcher.",
        reasoning_enabled=False,
        tool_usage=["DatabaseTool"],
        prompt={
            "context": "A senior analyst specializing in large dataset processing.",
            "instruction": "Senior Data Analyst: Analyze the data provided by the researcher.",
            "directive_function": "DualDirective",
            "source_attribute": "role, goal, backstory"
        },
        language_model=lm_gpt_4_turbo,
        config={"allow_delegation": "false"}
    )

    # Create Team
    comprehensive_crew_team = Team(
        title="ComprehensiveCrew",
        members=[primary_researcher, senior_analyst],
        coordination_pattern="Hierarchical",
        config={"verbose": "true"},
        memory_binding_scope="GroupShared",
        termination_condition="TaskCompletionTermination"
    )

    # Define Orchestration
    master_orchestrator_flow = Orchestration(
        title="MasterOrchestratorFlow",
        workflow_pattern="FlowWorkflowPattern_MasterOrchestratorFlow",
    )

    # Add Workflow Steps
    master_orchestrator_flow.workflow_steps([
        {"title": "initialize_system", "order": 1},
        {"title": "verification_router", "order": 2, "routing_logic":
            '''if self.state.topic:
                return "execute_crew"
            return "halt_system"'''
        },
        {"title": "run_crew_pipeline", "order": 3},
        {"title": "terminate", "order": 4},
    ])

    # Add Tasks
    data_gathering_task = Task(
        id="data_gathering",
        delegation_strategy="ExplicitAssignment",
        expected_output="A detailed report of raw data.",
        performed_by_agent=primary_researcher,
        prompt={
            "instruction": "Search the web for information.",
            "output_indicator": "A detailed report of raw data.",
            "source_attribute": "description, expected_output"
        },
        tool_usage=["web_search"]
    )

    analysis_phase_task = Task(
        id="analysis_phase",
        depends_on=data_gathering_task,
        delegation_strategy="ExplicitAssignment",
        dependency_type="ContextProviding",
        expected_output="A final analysis report.",
        guardrail_type="FunctionBased",
        human_checkpoint={"position": "AfterExecution", "type": "Review", "mandatory": True},
        output_schema={
            "type": "object",
            "properties": {
                "findings": {"type": "string", "description": "Key insights derived from data."},
                "confidence_score": {"type": "number", "description": "Score between 0.0 and 1.0"}
            },
            "required": ["findings", "confidence_score"]
        },
        performed_by_agent=senior_analyst,
        prompt={
            "instruction": "Analyze the raw data report.",
            "output_indicator": "A final analysis report.",
            "source_attribute": "description, expected_output"
        }
    )

    # Assign tasks to crew
    comprehensive_crew_team.assign_tasks([data_gathering_task, analysis_phase_task])

    # Add orchestrations and teams to the system
    comprehensive_system.add_orchestration(master_orchestrator_flow)
    comprehensive_system.add_team(comprehensive_crew_team)

    # Run the system
    comprehensive_system.run()

if __name__ == "__main__":
    main()
