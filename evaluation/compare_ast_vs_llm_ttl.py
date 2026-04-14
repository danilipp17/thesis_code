import os
import subprocess
from pathlib import Path
from collections import defaultdict
from rdflib import Graph, Namespace, RDF
from dotenv import load_dotenv

load_dotenv()

AGENTOSCIN = Namespace(
    "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
)


def run_extraction(
    source_dir: str, framework: str, system_name: str, out_ast: str, out_llm: str
):
    # Run AST
    ast_cmd = [
        "oscin",
        "extract",
        source_dir,
        "-f",
        framework,
        "-s",
        system_name,
        "-o",
        out_ast,
    ]
    print(f"Running AST extraction: {' '.join(ast_cmd)}")
    subprocess.run(ast_cmd, check=True)

    # Run LLM (needs OPENAI_API_KEY if we use openai, or ANTHROPIC_API_KEY. Default is anthropic? Let's specify --provider openai if supported)
    llm_cmd = [
        "oscin",
        "extract-llm",
        source_dir,
        "-o",
        out_llm,
        "--provider",
        "openai",
    ]
    print(f"Running LLM extraction: {' '.join(llm_cmd)}")
    try:
        subprocess.run(llm_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"LLM extraction failed: {e}")


def compare_ttls(ast_ttl: str, llm_ttl: str):
    ast_graph = Graph()
    llm_graph = Graph()

    ast_graph.parse(ast_ttl, format="turtle")
    if Path(llm_ttl).exists():
        llm_graph.parse(llm_ttl, format="turtle")

    categories = {
        "Agents": AGENTOSCIN.LLMAgent,
        "Tasks": AGENTOSCIN.Task,
        "Tools": AGENTOSCIN.Tool,
        "Teams": AGENTOSCIN.Team,
        "Workflow Steps": AGENTOSCIN.WorkflowStep,
    }

    edges = {
        "Agent -> Tool": AGENTOSCIN.agentToolUsage,
        "Team -> Agent": AGENTOSCIN.hasAgentMember,
        "Task -> Agent": AGENTOSCIN.performedByAgent,
        "Step -> Task": AGENTOSCIN.hasAssociatedTask,
        "Flow Edges (nextStep)": AGENTOSCIN.nextStep,
    }

    print("\n" + "=" * 60)
    print(f"STRUCTURAL EQUIVALENCE: AST vs LLM Baseline")
    print("=" * 60)

    print(f"{'Metric':<25} | {'AST Parser':<12} | {'LLM Baseline':<12}")
    print("-" * 55)

    for cat_name, class_uri in categories.items():
        ast_count = len(list(ast_graph.subjects(RDF.type, class_uri)))
        llm_count = len(list(llm_graph.subjects(RDF.type, class_uri)))
        print(f"{cat_name:<25} | {ast_count:<12} | {llm_count:<12}")

    print("-" * 55)
    for edge_name, prop_uri in edges.items():
        ast_count = len(list(ast_graph.triples((None, prop_uri, None))))
        llm_count = len(list(llm_graph.triples((None, prop_uri, None))))
        print(f"{edge_name:<25} | {ast_count:<12} | {llm_count:<12}")


if __name__ == "__main__":
    out_dir = Path("output/stress_compare")
    out_dir.mkdir(parents=True, exist_ok=True)

    # We will test on LangGraph stress test
    run_extraction(
        "evaluation/stress_tests/langgraph",
        "langgraph",
        "LangGraphStress",
        str(out_dir / "langgraph_ast.ttl"),
        str(out_dir / "langgraph_llm.ttl"),
    )
    compare_ttls(str(out_dir / "langgraph_ast.ttl"), str(out_dir / "langgraph_llm.ttl"))

    # CrewAI
    run_extraction(
        "evaluation/stress_tests/crewai",
        "crewai",
        "CrewAIStress",
        str(out_dir / "crewai_ast.ttl"),
        str(out_dir / "crewai_llm.ttl"),
    )
    compare_ttls(str(out_dir / "crewai_ast.ttl"), str(out_dir / "crewai_llm.ttl"))

    # AutoGen
    run_extraction(
        "evaluation/stress_tests/autogen",
        "autogen",
        "AutoGenStress",
        str(out_dir / "autogen_ast.ttl"),
        str(out_dir / "autogen_llm.ttl"),
    )
    compare_ttls(str(out_dir / "autogen_ast.ttl"), str(out_dir / "autogen_llm.ttl"))
