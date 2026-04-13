from rdflib import Graph, URIRef
from oscin.namespaces import AGENTOSCIN


def get_counts(graph_path):
    g = Graph()
    g.parse(graph_path, format="turtle")

    agents = len(
        list(
            g.subjects(
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                AGENTOSCIN.LLMAgent,
            )
        )
    )
    tools = len(
        list(
            g.subjects(
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                AGENTOSCIN.Tool,
            )
        )
    )
    tasks = len(
        list(
            g.subjects(
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                AGENTOSCIN.Task,
            )
        )
    )
    teams = len(
        list(
            g.subjects(
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                AGENTOSCIN.Team,
            )
        )
    )
    flows = len(
        list(
            g.subjects(
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                AGENTOSCIN.Orchestration,
            )
        )
    )
    steps = len(
        list(
            g.subjects(
                URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                AGENTOSCIN.WorkflowStep,
            )
        )
    )

    return {
        "Agents": agents,
        "Tools": tools,
        "Tasks": tasks,
        "Teams": teams,
        "Flows": flows,
        "Steps": steps,
    }


files = {
    "Original Custom System": "custom_system.ttl",
    "Extracted from CrewAI": "output/custom_extracted/crewai.ttl",
    "Extracted from LangGraph": "output/custom_extracted/langgraph.ttl",
    "Extracted from AutoGen": "output/custom_extracted/autogen.ttl",
}

print(
    f"{'Source':<30} | {'Agents':<6} | {'Tools':<5} | {'Tasks':<5} | {'Teams':<5} | {'Flows':<5} | {'Steps':<5}"
)
print("-" * 75)
for name, path in files.items():
    counts = get_counts(path)
    print(
        f"{name:<30} | {counts['Agents']:<6} | {counts['Tools']:<5} | {counts['Tasks']:<5} | {counts['Teams']:<5} | {counts['Flows']:<5} | {counts['Steps']:<5}"
    )
