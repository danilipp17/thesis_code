"""
evaluation.metrics.extraction_coverage
=======================================
Measures how completely and correctly the extraction pipeline captures
source code elements into the ontology TTL.

Compares the parser's intermediate representation (what was found in source)
against the individuals actually present in the extracted TTL graph.

Metrics produced:
- Per-element-type precision/recall/F1 (agents, tasks, tools, teams, flow steps)
- Relationship coverage (tool→agent, task→agent, team→members)
- Content coverage (string literals from source found in TTL)
- Overall extraction completeness score

Usage:
    result = compute(source_dir, extracted_ttl, framework)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF

from oscin.namespaces import AGENTOSCIN

NAME = "extraction_coverage"

log = logging.getLogger("oscin.eval.extraction_coverage")


def _local_name(uri) -> str:
    s = str(uri)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s


def _get_ttl_individuals_by_class(g: Graph) -> dict[str, set[str]]:
    """Get all ABox individuals grouped by ontology class local name."""
    tbox_prefix = str(AGENTOSCIN)
    result: dict[str, set[str]] = defaultdict(set)

    for s, _, o in g.triples((None, RDF.type, None)):
        if not isinstance(s, URIRef):
            continue
        if str(s).startswith(tbox_prefix):
            continue
        if isinstance(o, URIRef):
            o_str = str(o)
            if o_str.startswith("http://www.w3.org/"):
                continue
            result[_local_name(o)].add(_local_name(s))
    return dict(result)


def _get_ttl_literals(g: Graph) -> set[str]:
    """Collect all normalized literal strings from ABox triples."""
    tbox_prefix = str(AGENTOSCIN)
    values = set()
    for s, p, o in g:
        if isinstance(s, BNode) or isinstance(o, BNode):
            continue
        if isinstance(s, URIRef) and str(s).startswith(tbox_prefix):
            continue
        if isinstance(o, Literal) and str(o).strip():
            values.add(" ".join(str(o).split()).lower())
    return values


def _get_ttl_relationships(g: Graph) -> dict[str, list[tuple[str, str]]]:
    """Get relationships from TTL: predicate → [(subject_local, object_local)]."""
    tbox_prefix = str(AGENTOSCIN)
    rels: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for s, p, o in g:
        if isinstance(s, BNode) or isinstance(o, BNode):
            continue
        if isinstance(s, URIRef) and str(s).startswith(tbox_prefix):
            continue
        if not isinstance(s, URIRef) or not isinstance(o, URIRef):
            continue
        if not isinstance(p, URIRef):
            continue
        p_local = _local_name(p)
        # Only keep agentoscin predicates that represent relationships
        if str(AGENTOSCIN) in str(p):
            rels[p_local].append((_local_name(s), _local_name(o)))

    return dict(rels)


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _get_parser(framework: str, source_dir: Path):
    """Instantiate the appropriate parser for the framework."""
    from oscin.parsers import CrewAIParser, LangGraphParser, AutoGenParser

    parsers = {
        "crewai": CrewAIParser,
        "langgraph": LangGraphParser,
        "autogen": AutoGenParser,
    }
    parser_cls = parsers.get(framework)
    if not parser_cls:
        raise ValueError(f"Unknown framework: {framework}")
    return parser_cls(source_dir)


def compute(
    source_dir: Path | str,
    extracted_ttl: Path | str,
    framework: str,
) -> dict:
    """
    Compute extraction coverage by comparing parser output against TTL.

    Parameters
    ----------
    source_dir : Path
        The source directory to parse.
    extracted_ttl : Path
        The extracted TTL file to evaluate.
    framework : str
        Framework name (crewai, langgraph, autogen).

    Returns
    -------
    dict with coverage metrics.
    """
    source_dir = Path(source_dir)
    extracted_ttl = Path(extracted_ttl)

    if not source_dir.is_dir():
        return {"metric": NAME, "error": f"Source dir not found: {source_dir}"}
    if not extracted_ttl.is_file():
        return {"metric": NAME, "error": f"TTL not found: {extracted_ttl}"}

    # --- Step 1: Parse source to get intermediate representation ---
    try:
        parser = _get_parser(framework, source_dir)
        parser.parse_all()
    except Exception as e:
        return {"metric": NAME, "error": f"Parse failed: {type(e).__name__}: {e}"}

    # --- Step 2: Load extracted TTL ---
    try:
        g = Graph()
        g.parse(str(extracted_ttl), format="turtle")
    except Exception as e:
        return {"metric": NAME, "error": f"TTL parse failed: {type(e).__name__}: {e}"}

    ttl_individuals = _get_ttl_individuals_by_class(g)
    ttl_literals = _get_ttl_literals(g)
    ttl_rels = _get_ttl_relationships(g)

    # --- Step 3: Compare elements ---
    element_coverage = {}

    # Agents
    source_agents = set(parser.agents.keys())
    ttl_agents = ttl_individuals.get("LLMAgent", set()) | ttl_individuals.get("UserProxyAgent", set()) | ttl_individuals.get("ManagerAgent", set())
    # Normalize: TTL names are like "Agent_<key>"
    ttl_agent_keys = {
        name.replace("Agent_", "").lower() for name in ttl_agents
    }
    source_agent_keys = {k.lower() for k in source_agents}
    agent_matched = source_agent_keys & ttl_agent_keys
    agent_p = len(agent_matched) / len(ttl_agent_keys) if ttl_agent_keys else (1.0 if not source_agent_keys else 0.0)
    agent_r = len(agent_matched) / len(source_agent_keys) if source_agent_keys else 1.0
    element_coverage["agents"] = {
        "source_count": len(source_agents),
        "ttl_count": len(ttl_agents),
        "matched": len(agent_matched),
        "precision": round(agent_p, 3),
        "recall": round(agent_r, 3),
        "f1": round(_f1(agent_p, agent_r), 3),
        "missing": sorted(source_agent_keys - ttl_agent_keys),
        "extra": sorted(ttl_agent_keys - source_agent_keys),
    }

    # Tasks
    source_tasks = set(parser.tasks.keys())
    ttl_tasks = ttl_individuals.get("Task", set())
    ttl_task_keys = {name.replace("Task_", "").lower() for name in ttl_tasks}
    source_task_keys = {k.lower() for k in source_tasks}
    task_matched = source_task_keys & ttl_task_keys
    task_p = len(task_matched) / len(ttl_task_keys) if ttl_task_keys else (1.0 if not source_task_keys else 0.0)
    task_r = len(task_matched) / len(source_task_keys) if source_task_keys else 1.0
    element_coverage["tasks"] = {
        "source_count": len(source_tasks),
        "ttl_count": len(ttl_tasks),
        "matched": len(task_matched),
        "precision": round(task_p, 3),
        "recall": round(task_r, 3),
        "f1": round(_f1(task_p, task_r), 3),
        "missing": sorted(source_task_keys - ttl_task_keys),
        "extra": sorted(ttl_task_keys - source_task_keys),
    }

    # Tools
    source_tools = set(parser.tools.keys())
    ttl_tools = ttl_individuals.get("Tool", set())
    ttl_tool_keys = {name.replace("Tool_", "").lower() for name in ttl_tools}
    source_tool_keys = {k.lower() for k in source_tools}
    tool_matched = source_tool_keys & ttl_tool_keys
    tool_p = len(tool_matched) / len(ttl_tool_keys) if ttl_tool_keys else (1.0 if not source_tool_keys else 0.0)
    tool_r = len(tool_matched) / len(source_tool_keys) if source_tool_keys else 1.0
    element_coverage["tools"] = {
        "source_count": len(source_tools),
        "ttl_count": len(ttl_tools),
        "matched": len(tool_matched),
        "precision": round(tool_p, 3),
        "recall": round(tool_r, 3),
        "f1": round(_f1(tool_p, tool_r), 3),
        "missing": sorted(source_tool_keys - ttl_tool_keys),
        "extra": sorted(ttl_tool_keys - source_tool_keys),
    }

    # Teams
    source_teams = set(parser.teams.keys())
    ttl_teams = ttl_individuals.get("Team", set())
    ttl_team_keys = {name.replace("Team_", "").lower() for name in ttl_teams}
    source_team_keys = {k.lower() for k in source_teams}
    team_matched = source_team_keys & ttl_team_keys
    team_p = len(team_matched) / len(ttl_team_keys) if ttl_team_keys else (1.0 if not source_team_keys else 0.0)
    team_r = len(team_matched) / len(source_team_keys) if source_team_keys else 1.0
    element_coverage["teams"] = {
        "source_count": len(source_teams),
        "ttl_count": len(ttl_teams),
        "matched": len(team_matched),
        "precision": round(team_p, 3),
        "recall": round(team_r, 3),
        "f1": round(_f1(team_p, team_r), 3),
        "missing": sorted(source_team_keys - ttl_team_keys),
        "extra": sorted(ttl_team_keys - source_team_keys),
    }

    # Flow steps
    source_steps = set()
    if parser.flow:
        source_steps = {s.method_name.lower() for s in parser.flow.steps}
    ttl_flow_steps = set()
    for cls_name in ("FlowStep", "StartStep", "ConditionalStep", "EndStep",
                     "OrchestratorStep", "RouterStep"):
        ttl_flow_steps |= ttl_individuals.get(cls_name, set())
    ttl_step_keys = {name.split("_", 1)[-1].lower() if "_" in name else name.lower()
                     for name in ttl_flow_steps}
    step_matched = source_steps & ttl_step_keys
    step_p = len(step_matched) / len(ttl_step_keys) if ttl_step_keys else (1.0 if not source_steps else 0.0)
    step_r = len(step_matched) / len(source_steps) if source_steps else 1.0
    element_coverage["flow_steps"] = {
        "source_count": len(source_steps),
        "ttl_count": len(ttl_flow_steps),
        "matched": len(step_matched),
        "precision": round(step_p, 3),
        "recall": round(step_r, 3),
        "f1": round(_f1(step_p, step_r), 3),
        "missing": sorted(source_steps - ttl_step_keys),
        "extra": sorted(ttl_step_keys - source_steps),
    }

    # --- Step 4: Relationship coverage ---
    relationship_coverage = {}

    # Agent → Tool assignments
    source_agent_tools = set()
    for akey, agent in parser.agents.items():
        for tool_name in agent.tools:
            source_agent_tools.add((akey.lower(), tool_name.lower()))

    ttl_agent_tools = set()
    for pred in ("agentToolUsage",):
        for subj, obj in ttl_rels.get(pred, []):
            ttl_agent_tools.add((subj.replace("Agent_", "").lower(),
                                 obj.replace("Tool_", "").lower()))

    at_matched = source_agent_tools & ttl_agent_tools
    at_r = len(at_matched) / len(source_agent_tools) if source_agent_tools else 1.0
    relationship_coverage["agent_tool_assignments"] = {
        "source_count": len(source_agent_tools),
        "ttl_count": len(ttl_agent_tools),
        "recall": round(at_r, 3),
    }

    # Task → Agent assignments
    source_task_agents = set()
    for tkey, task in parser.tasks.items():
        if task.agent_key:
            source_task_agents.add((tkey.lower(), task.agent_key.lower()))

    ttl_task_agents = set()
    for pred in ("performedByAgent",):
        for subj, obj in ttl_rels.get(pred, []):
            ttl_task_agents.add((subj.replace("Task_", "").lower(),
                                 obj.replace("Agent_", "").lower()))

    ta_matched = source_task_agents & ttl_task_agents
    ta_r = len(ta_matched) / len(source_task_agents) if source_task_agents else 1.0
    relationship_coverage["task_agent_assignments"] = {
        "source_count": len(source_task_agents),
        "ttl_count": len(ttl_task_agents),
        "recall": round(ta_r, 3),
    }

    # Team → Agent membership
    source_team_members = set()
    for tkey, team in parser.teams.items():
        for akey in team.agent_keys:
            source_team_members.add((tkey.lower(), akey.lower()))

    ttl_team_members = set()
    for pred in ("hasAgentMember",):
        for subj, obj in ttl_rels.get(pred, []):
            ttl_team_members.add((subj.replace("Team_", "").lower(),
                                  obj.replace("Agent_", "").lower()))

    tm_matched = source_team_members & ttl_team_members
    tm_r = len(tm_matched) / len(source_team_members) if source_team_members else 1.0
    relationship_coverage["team_member_assignments"] = {
        "source_count": len(source_team_members),
        "ttl_count": len(ttl_team_members),
        "recall": round(tm_r, 3),
    }

    # --- Step 5: Content coverage (string literals) ---
    # Collect important string values from parser output
    source_strings = set()
    for agent in parser.agents.values():
        if agent.role:
            source_strings.add(" ".join(agent.role.split()).lower())
        if agent.goal:
            source_strings.add(" ".join(agent.goal.split()).lower())
        if agent.backstory:
            source_strings.add(" ".join(agent.backstory.split()).lower())
    for task in parser.tasks.values():
        if task.description:
            source_strings.add(" ".join(task.description.split()).lower())
        if task.expected_output:
            source_strings.add(" ".join(task.expected_output.split()).lower())
    for tool in parser.tools.values():
        if tool.description:
            source_strings.add(" ".join(tool.description.split()).lower())

    # Remove empty strings
    source_strings.discard("")

    # Check which source strings appear in TTL literals
    content_found = 0
    content_missing = []
    for src_str in source_strings:
        if src_str in ttl_literals:
            content_found += 1
        else:
            # Try substring match (TTL might have slightly different formatting)
            found = any(src_str in lit for lit in ttl_literals)
            if found:
                content_found += 1
            else:
                content_missing.append(src_str[:80])

    content_recall = content_found / len(source_strings) if source_strings else 1.0
    content_coverage = {
        "source_strings": len(source_strings),
        "found_in_ttl": content_found,
        "recall": round(content_recall, 3),
        "missing_sample": content_missing[:10],  # First 10 missing strings
    }

    # --- Step 6: Overall scores ---
    # Macro-average F1 across element types
    element_f1s = [
        element_coverage[k]["f1"]
        for k in ("agents", "tasks", "tools", "teams", "flow_steps")
        if element_coverage[k]["source_count"] > 0 or element_coverage[k]["ttl_count"] > 0
    ]
    element_macro_f1 = sum(element_f1s) / len(element_f1s) if element_f1s else 1.0

    # Relationship recall (macro avg)
    rel_recalls = [
        relationship_coverage[k]["recall"]
        for k in relationship_coverage
        if relationship_coverage[k]["source_count"] > 0
    ]
    relationship_avg_recall = sum(rel_recalls) / len(rel_recalls) if rel_recalls else 1.0

    # Combined score: 0.4 * element_f1 + 0.3 * relationship_recall + 0.3 * content_recall
    overall_score = (
        0.4 * element_macro_f1
        + 0.3 * relationship_avg_recall
        + 0.3 * content_recall
    )

    return {
        "metric": NAME,
        "framework": framework,
        "element_coverage": element_coverage,
        "relationship_coverage": relationship_coverage,
        "content_coverage": content_coverage,
        "element_macro_f1": round(element_macro_f1, 3),
        "relationship_avg_recall": round(relationship_avg_recall, 3),
        "content_recall": round(content_recall, 3),
        "overall_score": round(overall_score, 3),
    }


def row(result: dict) -> dict:
    """Flat fields for benchmark CSV."""
    return {
        "extraction_element_f1": result.get("element_macro_f1"),
        "extraction_rel_recall": result.get("relationship_avg_recall"),
        "extraction_content_recall": result.get("content_recall"),
        "extraction_overall": result.get("overall_score"),
    }


def summarize_markdown(result: dict) -> str:
    """Markdown summary for reports."""
    if "error" in result:
        return f"## Extraction Coverage\n- error: `{result['error']}`\n"

    lines = ["## Extraction Coverage"]
    lines.append("")
    lines.append(f"**Overall Score:** {result.get('overall_score', '–')}")
    lines.append(f"- Element Macro F1: {result.get('element_macro_f1', '–')}")
    lines.append(f"- Relationship Recall: {result.get('relationship_avg_recall', '–')}")
    lines.append(f"- Content Recall: {result.get('content_recall', '–')}")
    lines.append("")

    # Element breakdown
    lines.append("### Element Coverage")
    lines.append("")
    lines.append("| Element | Source | TTL | Matched | P | R | F1 |")
    lines.append("|---------|--------|-----|---------|---|---|----| ")
    for etype, data in (result.get("element_coverage") or {}).items():
        lines.append(
            f"| {etype} | {data['source_count']} | {data['ttl_count']} | "
            f"{data['matched']} | {data['precision']:.3f} | "
            f"{data['recall']:.3f} | {data['f1']:.3f} |"
        )

    # Relationships
    lines.append("")
    lines.append("### Relationship Coverage")
    lines.append("")
    for rtype, data in (result.get("relationship_coverage") or {}).items():
        lines.append(f"- **{rtype}**: {data['source_count']} source → {data['ttl_count']} TTL (recall={data['recall']:.3f})")

    # Content
    cc = result.get("content_coverage", {})
    lines.append("")
    lines.append(f"### Content Coverage")
    lines.append(f"- Source strings: {cc.get('source_strings', 0)}")
    lines.append(f"- Found in TTL: {cc.get('found_in_ttl', 0)}")
    lines.append(f"- Recall: {cc.get('recall', '–')}")

    return "\n".join(lines)
