import rdflib
from pathlib import Path


def evaluate():
    files = {
        "Original (Custom TTL)": "custom_system.ttl",
        "CrewAI Extracted": "output/custom_extracted/crewai.ttl",
        "LangGraph Extracted": "output/custom_extracted/langgraph.ttl",
        "AutoGen Extracted": "output/custom_extracted/autogen.ttl",
    }

    NS = rdflib.Namespace(
        "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
    )

    results = {}
    for name, path in files.items():
        g = rdflib.Graph()
        g.parse(path, format="turtle")

        # Entities
        agents = len(list(g.subjects(rdflib.RDF.type, NS.LLMAgent)))
        tools = len(list(g.subjects(rdflib.RDF.type, NS.Tool)))
        tasks = len(list(g.subjects(rdflib.RDF.type, NS.Task)))
        steps = len(list(g.subjects(rdflib.RDF.type, NS.WorkflowStep)))
        conditional_steps = len(list(g.subjects(rdflib.RDF.type, NS.ConditionalStep)))

        # Relations
        agent_tools = len(list(g.subject_objects(NS.agentToolUsage)))
        team_agents = len(list(g.subject_objects(NS.hasAgentMember)))

        # Tasks mapping (CrewAI uses performedByAgent, others might use hasAssociatedTask)
        task_agent = len(list(g.subject_objects(NS.performedByAgent)))
        step_task = len(list(g.subject_objects(NS.hasAssociatedTask)))

        # Control Flow (dependsOn or nextStep)
        step_depends = len(list(g.subject_objects(NS.dependsOn)))
        step_next = len(list(g.subject_objects(NS.nextStep)))

        # Patterns
        patterns = [
            str(o).split("#")[-1].split("/")[-1]
            for s, o in g.subject_objects(NS.employsCoordinationPattern)
        ]
        pattern = patterns[0] if patterns else "None"

        results[name] = {
            "Agents": agents,
            "Tools": tools,
            "Tasks": tasks,
            "Steps": steps,
            "Conditional": conditional_steps,
            "Agent->Tool": agent_tools,
            "Team->Agent": team_agents,
            "Task->Agent": task_agent,
            "Step->Task": step_task,
            "Flow Edges": step_depends + step_next,
            "Coord Pattern": pattern,
        }

    return results


if __name__ == "__main__":
    res = evaluate()

    # Print Markdown table
    headers = list(res["Original (Custom TTL)"].keys())
    print(f"| Source | " + " | ".join(headers) + " |")
    print(f"|--------|" + "|".join(["---"] * len(headers)) + "|")
    for name, metrics in res.items():
        row = f"| **{name}** | " + " | ".join(str(metrics[h]) for h in headers) + " |"
        print(row)
