from pathlib import Path
from oscin.intermediate import (
    ExtractedAgent,
    ExtractedTask,
    ExtractedTeam,
    ExtractedFlow,
    ExtractedFlowStep,
    ExtractedTool,
)
from oscin.populator import OntologyPopulator

# Build the Intermediate Representation
tool_search = ExtractedTool(
    class_name="web_search",
    name="Web Search",
    description="Search the web for recent events and news",
    args_schema_json='{"properties": {"query": {"type": "string"}}}',
    implementation_ref="tools.web_search",
    source_file="custom",
)

agent_researcher = ExtractedAgent(
    agent_key="researcher",
    role="Investigative Reporter",
    goal="Find the most interesting facts about a given topic.",
    backstory="You are a veteran reporter known for deep dives.",
    llm="gpt-4o",
    tools=["web_search"],
    source_file="custom",
)

agent_writer = ExtractedAgent(
    agent_key="writer",
    role="Creative Editor",
    goal="Write a compelling story based on facts.",
    backstory="You turn dry facts into captivating narratives.",
    llm="gpt-4o",
    tools=[],
    source_file="custom",
)

task_research = ExtractedTask(
    task_key="research_task",
    description="Research the latest news on AI breakthroughs.",
    expected_output="A list of 5 key facts.",
    agent_key="researcher",
    source_file="custom",
)

task_write = ExtractedTask(
    task_key="write_task",
    description="Draft an article based on the research.",
    expected_output="A 3-paragraph article.",
    agent_key="writer",
    source_file="custom",
)

team = ExtractedTeam(
    team_class_name="editorial_team",
    agent_keys=["researcher", "writer"],
    task_keys=["research_task", "write_task"],
    process="sequential",
    source_file="custom",
)

flow = ExtractedFlow(
    class_name="NewsPipeline",
    steps=[
        ExtractedFlowStep(
            method_name="start_research", step_type="start", dependencies=[]
        ),
        ExtractedFlowStep(
            method_name="review_research",
            step_type="conditional",
            dependencies=["start_research"],
            return_values=["good", "bad"],
        ),
        ExtractedFlowStep(
            method_name="write_article",
            step_type="regular",
            dependencies=["start_research"],
            calls_crew="editorial_team",
        ),
    ],
    source_file="custom",
)


# Mock the parser context
class MockParser:
    def __init__(self):
        self.system_name = "AI_News_System"
        self.framework_name = lambda: "CustomSource"
        self.tools = {"web_search": tool_search}
        self.agents = {"researcher": agent_researcher, "writer": agent_writer}
        self.tasks = {"research_task": task_research, "write_task": task_write}
        self.teams = {"editorial_team": team}
        self.flow = flow
        self.pydantic_models = {}

    def log_extraction_summary(self):
        pass


# Populate the ontology
parser = MockParser()
populator = OntologyPopulator(
    parser,
    system_name="AI_News_System",
    instance_namespace="http://example.org/instance#",
)
populator.populate()

output_path = Path(__file__).parent / "custom_system.ttl"
populator.g.serialize(destination=str(output_path), format="turtle")
print(f"Custom TTL generated at: {output_path}")
