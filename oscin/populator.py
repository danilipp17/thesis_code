"""
populator.py
============
Shared Ontology Populator for the OSCIN extraction pipeline.

This module takes framework-agnostic intermediate representations
(produced by any parser subclass) and creates OWL individuals with
property assertions in an RDFLib graph.

The populator is completely framework-independent — it reads only
from the ``BaseSourceParser`` dictionaries and never touches AST or
YAML.  Every method documents which mapping table row it implements.

The ontology vocabulary used is **agentoscin** as defined in
``agentoscin.ttl``.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Any

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from oscin.base_parser import BaseSourceParser
from oscin.namespaces import (
    AGENTO,
    AGENTOSCIN,
    CALLS_CREW,
    COORD_CUSTOM,
    COORD_HIERARCHICAL,
    COORD_NETWORK,
    COORD_REACT_LOOP,
    COORD_ROUND_ROBIN,
    COORD_SELECTOR_BASED,
    COORD_SEQUENTIAL,
    COORD_SWARM,
    HAS_DESCRIPTION,
    HAS_REFERENCE,
    HAS_TITLE,
    make_instance_namespace,
)
from oscin.utils import pydantic_fields_to_json_schema

log = logging.getLogger("oscin")


class OntologyPopulator:
    """
    Populates an RDF/OWL graph from extracted intermediate representations.

    The population follows the ontology property specification defined
    in ``agentoscin.ttl`` and the framework-specific mapping tables.
    Each method documents which mapping rule it implements.

    Parameters
    ----------
    parser : BaseSourceParser
        Any parser whose ``parse_all()`` has already been called.
    system_name : str
        Human-readable name for the AgenticSystem individual.
    instance_namespace : str
        Base URI for instance individuals (e.g.
        ``"http://example.org/email_flow#"``).
    """

    def __init__(
        self,
        parser: BaseSourceParser,
        system_name: str,
        instance_namespace: str = "http://example.org/instance#",
    ):
        self.parser = parser
        self.system_name = system_name
        self.EX = make_instance_namespace(instance_namespace)

        self.g = Graph()
        self._bind_namespaces()

        # Track created URIs for cross-referencing
        self.agent_uris: dict[str, URIRef] = {}
        self.task_uris: dict[str, URIRef] = {}
        self.tool_uris: dict[str, URIRef] = {}
        self.team_uris: dict[str, URIRef] = {}
        self.prompt_uris: dict[str, URIRef] = {}

    def _bind_namespaces(self) -> None:
        # Load the base ontology TBox (property & class declarations)
        # so that Protégé recognises ObjectProperties / DataProperties
        # instead of falling back to annotation properties.
        ontology_path = (
            Path(__file__).resolve().parent.parent / "ontology" / "agentoscin.ttl"
        )
        if ontology_path.is_file():
            self.g.parse(str(ontology_path), format="turtle")
            log.info("Loaded base ontology from %s", ontology_path)
        else:
            log.warning(
                "Base ontology not found at %s — output will lack TBox declarations",
                ontology_path,
            )

        self.g.bind("agentoscin", AGENTOSCIN)
        self.g.bind("agento", AGENTO)
        self.g.bind("ex", self.EX)
        self.g.bind("owl", OWL)
        self.g.bind("rdfs", RDFS)

        # Declare this output graph as an OWL ontology that imports the base schema
        onto_uri_str = str(self.EX).rstrip("#")
        onto_uri = URIRef(onto_uri_str)
        self.g.add((onto_uri, RDF.type, OWL.Ontology))

        base_ontology_uri = URIRef(str(AGENTOSCIN).rstrip("/"))
        self.g.add((onto_uri, OWL.imports, base_ontology_uri))

    # -----------------------------------------------------------
    # Public API
    # -----------------------------------------------------------

    def populate(self) -> Graph:
        """
        Execute the full ontology population pipeline.
        Order matters: tools and agents before tasks,
        tasks before teams, teams before flow.
        """
        log.info("")
        log.info("=" * 60)
        log.info("STARTING ONTOLOGY POPULATION")
        log.info("=" * 60)

        self._populate_tools()
        self._populate_agents()
        self._populate_tasks()
        self._populate_teams()
        self._populate_flow()
        self._populate_system()

        log.info("")
        log.info("=" * 60)
        log.info("ONTOLOGY POPULATION COMPLETE")
        log.info("  Total triples: %d", len(self.g))
        log.info("=" * 60)

        return self.g

    # -----------------------------------------------------------
    # Tool Population
    # Mapping table Section 5
    # -----------------------------------------------------------

    def _populate_tools(self) -> None:
        for key, tool in self.parser.tools.items():
            uri = self._create_individual("Tool", tool.class_name, AGENTO.Tool)
            self.tool_uris[key] = uri

            # Mapping table 5 assertions
            self._add_str(uri, HAS_TITLE, tool.name)
            self._add_str(uri, HAS_DESCRIPTION, tool.description)
            self._add_str(uri, AGENTOSCIN.hasInputSchema, tool.args_schema_json)
            self._add_str(
                uri, AGENTOSCIN.hasImplementationReference, tool.implementation_ref
            )

            log.info("  [Tool] %s \u2192 %s", tool.name, uri)

    # -----------------------------------------------------------
    # Agent Population
    # Mapping table Section 1
    # -----------------------------------------------------------

    def _populate_agents(self) -> None:
        for key, agent in self.parser.agents.items():
            uri = self._create_individual("Agent", key, AGENTO.LLMAgent)
            self.agent_uris[key] = uri

            # Basic Agent props (Mapping table 1)
            # agentID carries the source-level identifier (variable/class/key
            # name) so the reader can preserve original local-names across
            # round-trips, independent of the human-readable role string.
            self._add_str(uri, AGENTO.agentID, key)
            self._add_str(uri, AGENTO.agentRole, agent.role)
            if agent.agent_type:
                self._add_str(uri, AGENTOSCIN.agentType, agent.agent_type)
            self._add_bool(uri, AGENTOSCIN.hasReasoningEnabled, agent.reasoning)

            # --- Goal ---
            if agent.goal:
                goal_uri = self._create_individual("Goal", key, AGENTO.Goal)
                self._add_str(goal_uri, HAS_DESCRIPTION, agent.goal)
                self.g.add((uri, AGENTO.hasAgentGoal, goal_uri))

            # --- Agent Prompt(s) ---
            # Use directive_function from intermediate to determine prompt type
            directive = agent.directive_function

            if directive == "ModelDirective":
                prompt_uri = self._create_individual(
                    "AgentPrompt", key, AGENTO.Prompt
                )
                self.prompt_uris[f"agent_{key}"] = prompt_uri
                self._add_str(prompt_uri, AGENTO.promptInstruction, agent.goal)
                self._add_str(prompt_uri, AGENTO.promptContext, agent.backstory)
                self._add_str(
                    prompt_uri, AGENTOSCIN.hasDirectiveFunction, "ModelDirective"
                )
                if agent.prompt_source:
                    self._add_str(
                        prompt_uri, AGENTOSCIN.hasSourceAttribute, agent.prompt_source
                    )
                self.g.add((uri, AGENTO.agentPrompt, prompt_uri))

                if agent.description:
                    orch_prompt_uri = self._create_individual(
                        "OrchestratorPrompt", key, AGENTO.Prompt
                    )
                    self._add_str(
                        orch_prompt_uri,
                        AGENTO.promptInstruction,
                        agent.description,
                    )
                    self._add_str(
                        orch_prompt_uri,
                        AGENTOSCIN.hasDirectiveFunction,
                        "OrchestratorDirective",
                    )
                    self._add_str(
                        orch_prompt_uri,
                        AGENTOSCIN.hasSourceAttribute,
                        "description",
                    )
                    self.g.add((uri, AGENTO.agentPrompt, orch_prompt_uri))
            elif directive == "DualDirective":
                prompt_uri = self._create_individual(
                    "AgentPrompt", key, AGENTO.Prompt
                )
                self.prompt_uris[f"agent_{key}"] = prompt_uri

                instruction = (
                    f"{agent.role}: {agent.goal}" if agent.goal else agent.role
                )
                self._add_str(prompt_uri, AGENTO.promptInstruction, instruction)
                self._add_str(prompt_uri, AGENTO.promptContext, agent.backstory)
                self._add_str(
                    prompt_uri, AGENTOSCIN.hasDirectiveFunction, "DualDirective"
                )
                if agent.prompt_source:
                    self._add_str(
                        prompt_uri, AGENTOSCIN.hasSourceAttribute, agent.prompt_source
                    )
                self.g.add((uri, AGENTO.agentPrompt, prompt_uri))
            elif agent.goal or agent.backstory:
                prompt_uri = self._create_individual(
                    "AgentPrompt", key, AGENTO.Prompt
                )
                self.prompt_uris[f"agent_{key}"] = prompt_uri
                if agent.goal:
                    self._add_str(prompt_uri, AGENTO.promptInstruction, agent.goal)
                if agent.backstory:
                    self._add_str(prompt_uri, AGENTO.promptContext, agent.backstory)
                if directive:
                    self._add_str(
                        prompt_uri, AGENTOSCIN.hasDirectiveFunction, directive
                    )
                if agent.prompt_source:
                    self._add_str(
                        prompt_uri, AGENTOSCIN.hasSourceAttribute, agent.prompt_source
                    )
                self.g.add((uri, AGENTO.agentPrompt, prompt_uri))

            # --- Tool bindings ---
            for tool_key in agent.tools:
                tool_uri = self._resolve_or_create_tool(tool_key)
                self.g.add((uri, AGENTO.agentToolUsage, tool_uri))

            # --- Language Model ---
            if agent.llm:
                lm_uri = self._create_individual(
                    "LM", agent.llm, AGENTO.LanguageModel
                )
                self._add_str(lm_uri, HAS_TITLE, agent.llm)
                self.g.add((uri, AGENTO.useLanguageModel, lm_uri))

            # --- Agent-level config ---
            if agent.verbose is not None:
                self._add_config(
                    uri,
                    AGENTO.hasAgentConfig,
                    "verbose",
                    str(agent.verbose).lower(),
                )
            if agent.allow_delegation is not None:
                self._add_config(
                    uri,
                    AGENTO.hasAgentConfig,
                    "allow_delegation",
                    str(agent.allow_delegation).lower(),
                )

            # --- Reasoning ---
            if agent.reasoning:
                # Map the IR's reasoning_pattern to the matching ontology
                # subclass (ReAct, ChainOfThought, ReflectionLoop,
                # TreeOfThoughts). Unknown / empty → Unspecified.
                _rp_class_map = {
                    "ReAct": AGENTOSCIN.ReAct,
                    "ChainOfThought": AGENTOSCIN.ChainOfThought,
                    "ReflectionLoop": AGENTOSCIN.ReflectionLoop,
                    "TreeOfThoughts": AGENTOSCIN.TreeOfThoughts,
                }
                rp_class = _rp_class_map.get(
                    agent.reasoning_pattern, AGENTOSCIN.Unspecified
                )
                rp_suffix = (
                    agent.reasoning_pattern
                    if agent.reasoning_pattern in _rp_class_map
                    else "Unspecified"
                )
                rp_uri = self.EX[f"ReasoningPattern_{rp_suffix}"]
                self.g.add((rp_uri, RDF.type, rp_class))
                self.g.add((uri, AGENTOSCIN.employsReasoningPattern, rp_uri))
                # Use reasoning_origin from intermediate if set, else default
                origin = agent.reasoning_origin or "FrameworkManaged"
                self._add_str(uri, AGENTOSCIN.hasReasoningOrigin, origin)
                if agent.max_reasoning_attempts is not None:
                    self._add_int(
                        uri,
                        AGENTOSCIN.hasMaxReasoningAttempts,
                        agent.max_reasoning_attempts,
                    )

            # --- Memory ---
            if agent.memory:
                scope = "AgentPrivate"
                persistence = agent.memory_persistence or "Persistent"
                mb_uri = self._create_individual(
                    f"MemoryBinding_{scope}", key, AGENTOSCIN.MemoryBinding
                )
                mem_uri = self._create_individual(
                    f"Memory_{scope}", key, AGENTO.Memory
                )
                self._add_str(mb_uri, AGENTOSCIN.hasMemoryScope, scope)
                self._add_str(mem_uri, AGENTOSCIN.hasPersistenceScope, persistence)
                self.g.add((mb_uri, AGENTOSCIN.bindsMemory, mem_uri))
                self.g.add((uri, AGENTOSCIN.hasMemoryBinding, mb_uri))
                # Store memory type as title if available
                if agent.memory_type:
                    self._add_str(mem_uri, HAS_TITLE, agent.memory_type)

            # --- Knowledge Base ---
            for kb_source in getattr(agent, "knowledge_sources", []):
                kb_uri = self._create_individual(
                    "KnowledgeBase", kb_source, AGENTO.KnowledgeBase
                )
                self._add_str(kb_uri, HAS_TITLE, kb_source)
                self.g.add((uri, AGENTO.hasKnowledge, kb_uri))

            # --- Human Checkpoint (from Agent in AutoGen/LangGraph) ---
            if agent.human_input:
                hc_uri = self._create_individual(
                    "HumanCheckpoint", key, AGENTOSCIN.HumanCheckpoint
                )
                self.g.add((hc_uri, RDF.type, AGENTOSCIN.HumanCheckpoint))
                # Determine checkpoint type based on agent type
                if agent.agent_type == "UserProxy":
                    self._add_str(hc_uri, AGENTOSCIN.hasCheckpointType, "InputRequest")
                else:
                    self._add_str(hc_uri, AGENTOSCIN.hasCheckpointType, "Approval")
                self._add_bool(hc_uri, AGENTOSCIN.isMandatory, True)
                self.g.add((uri, AGENTOSCIN.hasHumanCheckpoint, hc_uri))

            log.info("  [Agent] %s \u2192 %s", agent.role, uri)

    # -----------------------------------------------------------
    # Task Population
    # Mapping table Section 2
    # -----------------------------------------------------------

    def _populate_tasks(self) -> None:
        for key, task in self.parser.tasks.items():
            uri = self._create_individual("Task", key, AGENTO.Task)
            self.task_uris[key] = uri

            # Basic Task attributes
            self._add_str(uri, AGENTOSCIN.hasExpectedOutput, task.expected_output)

            # --- Agent Assignment ---
            if task.agent_key and task.agent_key in self.agent_uris:
                self.g.add(
                    (uri, AGENTO.performedByAgent, self.agent_uris[task.agent_key])
                )
            # Only emit delegation strategy when parser explicitly set it
            if task.delegation_strategy:
                self._add_str(
                    uri, AGENTOSCIN.hasDelegationStrategy, task.delegation_strategy
                )

            # --- Task Prompt ---
            task_prompt_uri = self._create_individual(
                "TaskPrompt", key, AGENTO.Prompt
            )
            self.prompt_uris[f"task_{key}"] = task_prompt_uri

            self._add_str(
                task_prompt_uri, AGENTO.promptInstruction, task.description
            )
            self._add_str(
                task_prompt_uri, AGENTO.promptOutputIndicator, task.expected_output
            )
            if task.source_attribute:
                self._add_str(
                    task_prompt_uri,
                    AGENTOSCIN.hasSourceAttribute,
                    task.source_attribute,
                )

            self.g.add((uri, AGENTO.taskPrompt, task_prompt_uri))

            # --- Task-level tools ---
            for tool_name in task.tools:
                tool_uri = self._resolve_or_create_tool(tool_name)
                self.g.add((uri, AGENTOSCIN.taskToolUsage, tool_uri))

            # --- Output Schema ---
            if (
                task.output_pydantic
                and task.output_pydantic in self.parser.pydantic_models
            ):
                model = self.parser.pydantic_models[task.output_pydantic]
                schema_uri = self._create_individual(
                    "Schema", task.output_pydantic, AGENTOSCIN.Schema
                )
                schema_json = pydantic_fields_to_json_schema(model.fields)
                self._add_str(schema_uri, AGENTOSCIN.hasSchemaDefinition, schema_json)
                self._add_str(schema_uri, HAS_TITLE, task.output_pydantic)
                self._add_str(
                    schema_uri, AGENTOSCIN.hasSourceAttribute, "output_pydantic"
                )
                self.g.add((uri, AGENTOSCIN.hasOutputSchema, schema_uri))

            if task.output_json:
                schema_uri = self._create_individual(
                    "Schema", f"{task.output_json}_json", AGENTOSCIN.Schema
                )
                self._add_str(schema_uri, HAS_TITLE, task.output_json)
                self._add_str(
                    schema_uri, AGENTOSCIN.hasSourceAttribute, "output_json"
                )
                self.g.add((uri, AGENTOSCIN.hasOutputSchema, schema_uri))

            # --- Dependencies ---
            for dep_key in task.context_tasks:
                if dep_key in self.task_uris:
                    self.g.add((uri, AGENTOSCIN.dependsOn, self.task_uris[dep_key]))
                else:
                    # Often the dependency might refer to a task extracted later or with slightly different key
                    # Let's create a stub if not found
                    dep_uri = self.EX[f"Task_{self._safe_id(dep_key)}"]
                    self.g.add((dep_uri, RDF.type, AGENTO.Task))
                    self.g.add((uri, AGENTOSCIN.dependsOn, dep_uri))
            if task.context_tasks:
                self._add_str(uri, AGENTOSCIN.hasDependencyType, "ContextProviding")

            # --- Guardrails ---
            for i, guardrail_str in enumerate(task.guardrails):
                gr_uri = self._create_individual(
                    "Guardrail", f"{key}_{i}", AGENTOSCIN.Guardrail
                )
                self.g.add((gr_uri, RDF.type, AGENTOSCIN.Guardrail))

                # C1: Parse structured guardrail type
                if guardrail_str.startswith("FunctionBased:"):
                    self._add_str(gr_uri, AGENTOSCIN.hasGuardrailType, "FunctionBased")
                    detail = guardrail_str[len("FunctionBased:") :]
                    self._add_str(gr_uri, AGENTOSCIN.hasValidationLogic, detail)
                elif guardrail_str.startswith("LLMBased:"):
                    self._add_str(gr_uri, AGENTOSCIN.hasGuardrailType, "LLMBased")
                    detail = guardrail_str[len("LLMBased:") :]
                    self._add_str(gr_uri, HAS_DESCRIPTION, detail)
                else:
                    self._add_str(gr_uri, HAS_DESCRIPTION, guardrail_str)

                # C2: hasMaxRetries from CrewAI guardrail_max_retries kwarg.
                # Applied to every guardrail on the task (CrewAI's
                # guardrail_max_retries is a task-level setting that
                # governs retries across all guardrails on that task).
                if task.guardrail_max_retries is not None:
                    self._add_int(
                        gr_uri,
                        AGENTOSCIN.hasMaxRetries,
                        task.guardrail_max_retries,
                    )

                self.g.add((uri, AGENTOSCIN.hasGuardrail, gr_uri))

            # --- Human Checkpoint ---
            if task.human_input:
                hc_uri = self._create_individual(
                    "HumanCheckpoint", key, AGENTOSCIN.HumanCheckpoint
                )
                self.g.add(
                    (hc_uri, RDF.type, AGENTOSCIN.HumanCheckpoint)
                )  # ensure type
                self._add_str(hc_uri, AGENTOSCIN.hasCheckpointType, "Review")
                self._add_str(
                    hc_uri, AGENTOSCIN.hasCheckpointPosition, "AfterExecution"
                )
                self._add_bool(hc_uri, AGENTOSCIN.isMandatory, True)
                self.g.add((uri, AGENTOSCIN.hasHumanCheckpoint, hc_uri))

            log.info("  [Task] %s \u2192 %s", key, uri)

    # -----------------------------------------------------------
    # Team Population
    # Mapping table Section 3
    # -----------------------------------------------------------

    def _populate_teams(self) -> None:
        for key, team in self.parser.teams.items():
            uri = self._create_individual("Team", key, AGENTO.Team)
            self.team_uris[key] = uri
            self._add_str(uri, HAS_TITLE, team.team_class_name)

            # --- Agent Members ---
            for agent_key in team.agent_keys:
                if agent_key in self.agent_uris:
                    self.g.add(
                        (uri, AGENTO.hasAgentMember, self.agent_uris[agent_key])
                    )

            # --- Coordination Pattern ---
            # Use explicit coordination_pattern if set, else infer from process
            coord_pattern_map = {
                "Sequential": COORD_SEQUENTIAL,
                "Hierarchical": COORD_HIERARCHICAL,
                "RoundRobin": COORD_ROUND_ROBIN,
                "SelectorBased": COORD_SELECTOR_BASED,
                "Swarm": COORD_SWARM,
                "ReActLoop": COORD_REACT_LOOP,
                "Network": COORD_NETWORK,
                "Custom": COORD_CUSTOM,
            }
            process_map = {
                "sequential": COORD_SEQUENTIAL,
                "hierarchical": COORD_HIERARCHICAL,
            }
            if (
                team.coordination_pattern
                and team.coordination_pattern in coord_pattern_map
            ):
                pattern_uri = coord_pattern_map[team.coordination_pattern]
            else:
                pattern_uri = process_map.get(team.process, COORD_CUSTOM)
            self.g.add((pattern_uri, RDF.type, AGENTOSCIN.CoordinationPattern))
            self.g.add((uri, AGENTOSCIN.employsCoordinationPattern, pattern_uri))

            # --- Termination ---
            # Only emit termination conditions that were explicitly declared by the parser
            if team.termination_conditions:
                # Structured termination conditions from parser
                self._populate_termination_conditions(
                    uri, key, team.termination_conditions
                )

            # Turn-limit termination (e.g. AutoGen max_turns)
            # Skip if a TurnLimit condition is already present in
            # termination_conditions (avoid duplicating when max_turns
            # was promoted from a composite sub-condition).
            if team.max_turns is not None:
                has_top_level_turn_limit = any(
                    tc.get("type") == "TurnLimit" and tc.get("max_turns") == team.max_turns
                    for tc in team.termination_conditions
                )
                if not has_top_level_turn_limit:
                    tl_uri = self._create_individual(
                        "TurnLimit", key, AGENTOSCIN.TurnLimitTermination
                    )
                    self._add_int(tl_uri, AGENTOSCIN.hasMaxTurns, team.max_turns)
                    self.g.add((uri, AGENTOSCIN.hasTerminationCondition, tl_uri))

            # --- Workflow Pattern ---
            # Only create team-level sequential workflow steps for teams
            # that have explicitly ordered tasks (CrewAI crews from YAML).
            # LangGraph and AutoGen teams have auto-synthesized task_keys
            # whose ordering doesn't represent a real workflow — the Flow
            # pattern is the authoritative workflow for those frameworks.
            if team.task_keys and team.coordination_pattern not in (
                "RoundRobin",
                "SelectorBased",
                "Swarm",
                "ReActLoop",
                "Custom",
                "Network",
            ):
                wp_uri = self._create_individual(
                    "WorkflowPattern", key, AGENTO.WorkflowPattern
                )
                self.g.add((uri, AGENTO.hasWorkflowPattern, wp_uri))

                prev_step_uri = None
                for idx, task_key in enumerate(team.task_keys):
                    step_uri = self.EX[
                        f"CrewStep_{self._safe_id(key)}_{self._safe_id(task_key)}"
                    ]

                    # Determine type
                    is_first = idx == 0
                    is_last = idx == len(team.task_keys) - 1
                    if is_first and is_last:
                        self.g.add((step_uri, RDF.type, AGENTO.StartStep))
                        self.g.add((step_uri, RDF.type, AGENTO.EndStep))
                    elif is_first:
                        self.g.add((step_uri, RDF.type, AGENTO.StartStep))
                    elif is_last:
                        self.g.add((step_uri, RDF.type, AGENTO.EndStep))
                    else:
                        self.g.add((step_uri, RDF.type, AGENTO.WorkflowStep))

                    self._add_str(step_uri, HAS_TITLE, task_key)
                    self._add_int(step_uri, AGENTO.stepOrder, idx + 1)

                    if task_key in self.task_uris:
                        self.g.add(
                            (
                                step_uri,
                                AGENTO.hasAssociatedTask,
                                self.task_uris[task_key],
                            )
                        )

                    if prev_step_uri is not None:
                        self.g.add((prev_step_uri, AGENTO.nextStep, step_uri))

                    self.g.add((wp_uri, AGENTO.hasWorkflowStep, step_uri))

                    # C3: For sequential teams, add implicit Sequential dependency
                    # between consecutive tasks that don't have explicit context
                    if (
                        team.process == "sequential"
                        and prev_step_uri is not None
                        and task_key in self.task_uris
                        and idx > 0
                    ):
                        prev_task_key = team.task_keys[idx - 1]
                        task_obj = self.parser.tasks.get(task_key)
                        if task_obj and not task_obj.context_tasks:
                            # No explicit context → add sequential dependency
                            if prev_task_key in self.task_uris:
                                self.g.add(
                                    (
                                        self.task_uris[task_key],
                                        AGENTOSCIN.dependsOn,
                                        self.task_uris[prev_task_key],
                                    )
                                )
                                self._add_str(
                                    self.task_uris[task_key],
                                    AGENTOSCIN.hasDependencyType,
                                    "Sequential",
                                )

                    prev_step_uri = step_uri

            # --- Manager Agent (hierarchical process) ---
            if team.manager_llm or team.manager_agent:
                manager_key = team.manager_agent or f"manager_{key}"
                if manager_key not in self.agent_uris:
                    manager_uri = self._create_individual(
                        "Agent", manager_key, AGENTO.LLMAgent
                    )
                    self.agent_uris[manager_key] = manager_uri
                    self._add_str(manager_uri, AGENTO.agentID, manager_key)
                    self._add_str(manager_uri, AGENTO.agentRole, "Manager")
                    self._add_str(manager_uri, AGENTOSCIN.agentType, "Manager")
                    if team.manager_llm:
                        lm_uri = self._create_individual(
                            "LM", team.manager_llm, AGENTO.LanguageModel
                        )
                        self._add_str(lm_uri, HAS_TITLE, team.manager_llm)
                        self.g.add((manager_uri, AGENTO.useLanguageModel, lm_uri))
                    self.g.add((uri, AGENTO.hasAgentMember, manager_uri))
                    log.info("  [Agent] Manager created for team '%s'", key)

            # --- Config & Memory ---
            if team.verbose:
                self._add_config(uri, AGENTO.hasSystemConfig, "verbose", "true")
            if team.memory:
                self._bind_memory(uri, key, "GroupShared")

            # --- Knowledge Base ---
            for kb_source in getattr(team, "knowledge_sources", []):
                kb_uri = self._create_individual(
                    "KnowledgeBase", kb_source, AGENTO.KnowledgeBase
                )
                self._add_str(kb_uri, HAS_TITLE, kb_source)
                self.g.add((uri, AGENTO.hasKnowledge, kb_uri))

            log.info("  [Team] %s \u2192 %s (process: %s)", key, uri, team.process)

    # -----------------------------------------------------------
    # Termination Condition Population
    # -----------------------------------------------------------

    def _populate_termination_conditions(
        self, team_uri: URIRef, team_key: str, conditions: list[dict]
    ) -> None:
        """Populate structured termination conditions from parser data."""
        for i, tc in enumerate(conditions):
            tc_type = tc.get("type", "")
            suffix = f"{team_key}_{i}"

            if tc_type == "EventBased":
                tc_uri = self._create_individual(
                    "EventTermination", suffix, AGENTOSCIN.EventBasedTermination
                )
                trigger = tc.get("trigger", "")
                if trigger:
                    self._add_str(tc_uri, AGENTOSCIN.hasTriggerExpression, trigger)
                self.g.add((team_uri, AGENTOSCIN.hasTerminationCondition, tc_uri))

            elif tc_type == "TurnLimit":
                tc_uri = self._create_individual(
                    "TurnLimit", suffix, AGENTOSCIN.TurnLimitTermination
                )
                max_turns = tc.get("max_turns")
                if max_turns is not None:
                    self._add_int(tc_uri, AGENTOSCIN.hasMaxTurns, int(max_turns))
                self.g.add((team_uri, AGENTOSCIN.hasTerminationCondition, tc_uri))

            elif tc_type == "Routing":
                tc_uri = self._create_individual(
                    "RoutingTermination", suffix, AGENTOSCIN.RoutingTermination
                )
                self.g.add((team_uri, AGENTOSCIN.hasTerminationCondition, tc_uri))

            elif tc_type == "Composite":
                comp_uri = self._create_individual(
                    "CompositeTermination", suffix, AGENTOSCIN.CompositeTermination
                )
                operator = tc.get("operator", "OR")
                self._add_str(comp_uri, AGENTOSCIN.hasOperator, operator)
                # Recurse for sub-conditions
                sub_conditions = tc.get("conditions", [])
                for j, sub_tc in enumerate(sub_conditions):
                    sub_suffix = f"{suffix}_sub{j}"
                    sub_type = sub_tc.get("type", "")
                    if sub_type == "EventBased":
                        sub_uri = self._create_individual(
                            "EventTermination",
                            sub_suffix,
                            AGENTOSCIN.EventBasedTermination,
                        )
                        trigger = sub_tc.get("trigger", "")
                        if trigger:
                            self._add_str(
                                sub_uri, AGENTOSCIN.hasTriggerExpression, trigger
                            )
                        self.g.add((comp_uri, AGENTOSCIN.hasSubCondition, sub_uri))
                    elif sub_type == "TurnLimit":
                        sub_uri = self._create_individual(
                            "TurnLimit", sub_suffix, AGENTOSCIN.TurnLimitTermination
                        )
                        max_turns = sub_tc.get("max_turns")
                        if max_turns is not None:
                            self._add_int(
                                sub_uri, AGENTOSCIN.hasMaxTurns, int(max_turns)
                            )
                        self.g.add((comp_uri, AGENTOSCIN.hasSubCondition, sub_uri))
                self.g.add((team_uri, AGENTOSCIN.hasTerminationCondition, comp_uri))

    # -----------------------------------------------------------
    # Flow Population
    # Mapping table Section 4
    # -----------------------------------------------------------

    def _populate_flow(self) -> None:
        flow = self.parser.flow
        if not flow:
            log.info("  [Flow] No Flow class found \u2014 skipping.")
            return

        orch_uri = self._setup_orchestration_metadata(flow)

        # Mapping table 4: Crew references
        for crew_ref in flow.crew_references:
            if crew_ref in self.team_uris:
                self.g.add(
                    (orch_uri, AGENTOSCIN.orchestratesTeam, self.team_uris[crew_ref])
                )

        wp_uri = self._create_individual(
            "FlowWorkflowPattern", flow.class_name, AGENTO.WorkflowPattern
        )
        self.g.add((orch_uri, AGENTO.hasWorkflowPattern, wp_uri))

        step_uris, outgoing_edges, conditional_step_names = self._create_flow_steps(flow, wp_uri)
        self._resolve_flow_edges(flow, step_uris, outgoing_edges, conditional_step_names)

        log.info(
            "  [Flow] %s \u2192 %s (%d steps, %d crew references)",
            flow.class_name,
            orch_uri,
            len(flow.steps),
            len(flow.crew_references),
        )

    def _setup_orchestration_metadata(self, flow) -> URIRef:
        uri = self._create_individual(
            "Orchestration", flow.class_name, AGENTOSCIN.Orchestration
        )
        self._add_str(uri, HAS_TITLE, flow.class_name)

        # Infer coordination pattern from flow topology
        coord_pattern = self._infer_orchestration_pattern(flow)
        self.g.add((coord_pattern, RDF.type, AGENTOSCIN.CoordinationPattern))
        self.g.add((uri, AGENTOSCIN.employsCoordinationPattern, coord_pattern))

        # Store state schema if present (e.g. LangGraph TypedDict fields)
        if hasattr(flow, "state_fields") and flow.state_fields:
            import json

            schema_uri = self._create_individual(
                "StateSchema", flow.class_name, AGENTOSCIN.Schema
            )
            self._add_str(
                schema_uri,
                AGENTOSCIN.hasSchemaDefinition,
                json.dumps(flow.state_fields, sort_keys=True),
            )
            if flow.state_model:
                self._add_str(schema_uri, HAS_TITLE, flow.state_model)
            self._add_str(
                schema_uri, AGENTOSCIN.hasSourceAttribute, "state_model"
            )
            self.g.add((uri, AGENTOSCIN.hasOutputSchema, schema_uri))

        return uri

    @staticmethod
    def _infer_orchestration_pattern(flow) -> URIRef:
        step_types = {s.step_type for s in flow.steps}
        has_conditional = "conditional" in step_types or "router" in step_types
        has_loop = any(
            s.step_type in ("conditional", "router")
            and s.method_name in s.return_values
            for s in flow.steps
        )

        if not has_conditional:
            return COORD_SEQUENTIAL
        if has_loop:
            return COORD_REACT_LOOP
        return COORD_HIERARCHICAL

    def _create_flow_steps(
        self, flow, wp_uri: URIRef
    ) -> tuple[dict[str, URIRef], dict[str, list[str]], set[str]]:
        step_uris: dict[str, URIRef] = {}
        outgoing_edges: dict[str, list[str]] = {}
        conditional_step_names: set[str] = set()

        for idx, step in enumerate(flow.steps):
            uri = self._create_individual(
                "FlowStep", step.method_name, AGENTO.WorkflowStep
            )
            step_uris[step.method_name] = uri
            outgoing_edges[step.method_name] = []

            # Determine specific step types
            if step.step_type == "start":
                self.g.add((uri, RDF.type, AGENTO.StartStep))
            elif step.step_type == "router":
                self.g.add((uri, RDF.type, AGENTOSCIN.ConditionalStep))
                conditional_step_names.add(step.method_name)
            elif step.step_type == "conditional":
                self.g.add((uri, RDF.type, AGENTOSCIN.ConditionalStep))
                conditional_step_names.add(step.method_name)

            # Store routing logic if present (routers, or start nodes
            # with conditional edges in LangGraph)
            if step.function_body and not step.function_body.startswith(
                "routing_function:"
            ):
                self._add_str(uri, AGENTOSCIN.hasRoutingLogic, step.function_body)
                # Mark as conditional even if also a start step
                if step.step_type != "router":
                    self.g.add((uri, RDF.type, AGENTOSCIN.ConditionalStep))
                    conditional_step_names.add(step.method_name)
            elif step.step_type == "router" and step.function_body:
                self._add_str(uri, AGENTOSCIN.hasRoutingLogic, step.function_body)

            # Store edge mapping if present (label → target node mapping)
            if step.edge_mapping:
                import json

                self._add_str(
                    uri,
                    AGENTOSCIN.hasEdgeMapping,
                    json.dumps(step.edge_mapping, sort_keys=True),
                )

            self._add_str(uri, HAS_TITLE, step.method_name)
            self._add_int(uri, AGENTO.stepOrder, idx + 1)
            self.g.add((wp_uri, AGENTO.hasWorkflowStep, uri))

            # Link step to its associated agent (e.g. LangGraph node → LLMAgent)
            if step.associated_agent_key and step.associated_agent_key in self.agent_uris:
                self.g.add(
                    (
                        uri,
                        AGENTOSCIN.hasAssociatedAgent,
                        self.agent_uris[step.associated_agent_key],
                    )
                )

            # Store per-step crew binding (e.g. CrewAI @listen calling crew.kickoff())
            if step.calls_crew:
                self._add_str(uri, CALLS_CREW, step.calls_crew)

            # Store aggregation combinator for multi-predecessor decorators
            if step.aggregation_combinator:
                self._add_str(
                    uri, AGENTOSCIN.hasAggregationCombinator, step.aggregation_combinator
                )

        # Persist literal decorator arguments (e.g. CrewAI @start("wait_next_run"))
        # as :hasDecoratorArgument so they survive the round-trip. Method-name
        # references are already captured by the nextStep edge structure, so
        # we don't duplicate them.
        method_names = {s.method_name for s in flow.steps}
        for step in flow.steps:
            uri = step_uris[step.method_name]
            for dep in step.dependencies:
                if dep and dep not in method_names:
                    self._add_str(uri, AGENTOSCIN.hasDecoratorArgument, dep)

        return step_uris, outgoing_edges, conditional_step_names

    def _resolve_flow_edges(
        self, flow, step_uris: dict[str, URIRef], outgoing_edges: dict[str, list[str]],
        conditional_step_names: set[str] | None = None,
    ) -> None:
        # Resolve target mapping: @listen("label") or method names
        # First pass: map step names to their own URIs
        label_map: dict[str, URIRef] = {}
        for step in flow.steps:
            label_map[step.method_name] = step_uris[step.method_name]
        # Second pass: add listener labels (only if not already mapped)
        # This handles CrewAI @listen("label") patterns without
        # overriding step_name → URI mappings needed by LangGraph.
        for step in flow.steps:
            if step.step_type in ("listen", "regular", "start"):
                for arg in step.dependencies:
                    if arg not in label_map:
                        label_map[arg] = step_uris[step.method_name]

        # Connect edges
        for step in flow.steps:
            src_uri = step_uris[step.method_name]

            # Direct outgoing edges recorded by the parser (e.g. LangGraph
            # add_edge("a","b") incl. back-edges that close ReAct loops).
            # rdflib dedupes triples, so this is safe even if a later branch
            # adds the same edge again.
            for tgt in step.outgoing:
                if tgt in label_map:
                    self.g.add((src_uri, AGENTO.nextStep, label_map[tgt]))
                    outgoing_edges[step.method_name].append(tgt)

            # Steps with return_values (routers, or start nodes with
            # conditional edges in LangGraph)
            if step.return_values:
                for ret_val in step.return_values:
                    if ret_val in label_map:
                        self.g.add((src_uri, AGENTO.nextStep, label_map[ret_val]))
                        outgoing_edges[step.method_name].append(ret_val)

            # For any step (not just start), create nextStep edges to steps
            # whose dependencies reference this step by method name.
            # This captures @listen(method) and @router(method) patterns.
            if not step.return_values:
                for other in flow.steps:
                    if other.method_name == step.method_name:
                        continue
                    if any(arg == step.method_name for arg in other.dependencies):
                        self.g.add(
                            (
                                src_uri,
                                AGENTO.nextStep,
                                step_uris[other.method_name],
                            )
                        )
                        outgoing_edges[step.method_name].append(other.method_name)

        # Reclassify dead-ends as EndSteps (keep WorkflowStep as parent type).
        # Skip conditional/router steps — they may have zero resolved edges
        # because their routing targets didn't map to step URIs, but they
        # are NOT terminal steps.
        # Also skip steps that are already StartSteps — a start node
        # cannot also be a terminal node in a non-trivial flow.
        conditional = conditional_step_names or set()
        start_step_names = {
            s.method_name for s in flow.steps if s.step_type == "start"
        }
        for step_name, edges in outgoing_edges.items():
            if not edges and step_name not in conditional and step_name not in start_step_names:
                uri = step_uris[step_name]
                self.g.add((uri, RDF.type, AGENTO.EndStep))

    # -----------------------------------------------------------
    # System-Level Population
    # Mapping table Section 6
    # -----------------------------------------------------------

    def _populate_system(self) -> None:
        sys_uri = self.EX[self._safe_id(self.system_name)]
        self.g.add((sys_uri, RDF.type, AGENTOSCIN.AgenticSystem))

        self._add_str(sys_uri, HAS_TITLE, self.system_name)
        self._add_str(
            sys_uri, AGENTOSCIN.hasSourceFramework, self.parser.framework_name()
        )

        # Link containers
        for team_uri in self.team_uris.values():
            self.g.add((sys_uri, AGENTOSCIN.containsTeam, team_uri))
        for agent_uri in self.agent_uris.values():
            self.g.add((sys_uri, AGENTOSCIN.containsAgent, agent_uri))

        if self.parser.flow:
            orch_uri = self.EX[
                f"Orchestration_{self._safe_id(self.parser.flow.class_name)}"
            ]
            self.g.add((sys_uri, AGENTOSCIN.containsOrchestration, orch_uri))

        log.info("  [System] %s \u2192 %s", self.system_name, sys_uri)

    # -----------------------------------------------------------
    # Refined Helpers
    # -----------------------------------------------------------

    def _resolve_or_create_tool(self, tool_key: str) -> URIRef:
        """
        Return the URI for a tool, creating a stub for external tools
        that were not found in the parsed source files.
        """
        if tool_key in self.tool_uris:
            return self.tool_uris[tool_key]

        # Create a minimal Tool individual for an external/imported tool
        uri = self._create_individual("Tool", tool_key, AGENTO.Tool)
        self.tool_uris[tool_key] = uri
        self._add_str(uri, HAS_TITLE, tool_key)
        self._add_str(uri, HAS_REFERENCE, f"external:{tool_key}")
        log.info("  [Tool] Created external stub for '%s' → %s", tool_key, uri)
        return uri

    def _create_individual(self, prefix: str, key: str, owl_class: URIRef) -> URIRef:
        """Create a URI and declare its RDF:type."""
        uri = self.EX[f"{prefix}_{self._safe_id(key)}"]
        self.g.add((uri, RDF.type, owl_class))
        return uri

    def _bind_memory(self, parent_uri: URIRef, key: str, scope: str) -> None:
        """Standardized memory instantiation for Agents and Teams."""
        mb_uri = self._create_individual(
            f"MemoryBinding_{scope}", key, AGENTOSCIN.MemoryBinding
        )
        mem_uri = self._create_individual(f"Memory_{scope}", key, AGENTO.Memory)

        self._add_str(mb_uri, AGENTOSCIN.hasMemoryScope, scope)
        self._add_str(mem_uri, AGENTOSCIN.hasPersistenceScope, "Persistent")
        self.g.add((mb_uri, AGENTOSCIN.bindsMemory, mem_uri))

        prop = (
            AGENTOSCIN.hasTeamMemoryBinding
            if scope == "GroupShared"
            else AGENTOSCIN.hasMemoryBinding
        )
        self.g.add((parent_uri, prop, mb_uri))

    def _add_str(self, subject: URIRef, predicate: URIRef, text: str | None) -> None:
        if text:
            self.g.add((subject, predicate, Literal(text, datatype=XSD.string)))

    def _add_int(self, subject: URIRef, predicate: URIRef, val: int | None) -> None:
        if val is not None:
            self.g.add((subject, predicate, Literal(val, datatype=XSD.integer)))

    def _add_bool(self, subject: URIRef, predicate: URIRef, val: bool | None) -> None:
        if val is not None:
            self.g.add((subject, predicate, Literal(val, datatype=XSD.boolean)))

    def _add_config(
        self, subject: URIRef, property_uri: URIRef, key: str, value: str
    ) -> None:
        c_uri = self.EX[
            f"Config_{self._safe_id(key)}_{self._safe_id(str(subject).split('#')[-1])}"
        ]
        self.g.add((c_uri, RDF.type, AGENTO.Config))
        self._add_str(c_uri, AGENTO.configKey, key)
        self._add_str(c_uri, AGENTO.configValue, value)
        self.g.add((subject, property_uri, c_uri))

    @staticmethod
    def _safe_id(name: str) -> str:
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")


def print_validation_report(graph: Graph, parser: BaseSourceParser) -> None:
    """Print extraction and population summary."""
    type_counts: dict[str, int] = {}
    for s, p, o in graph.triples((None, RDF.type, None)):
        type_name = str(o).split("/")[-1]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    print("\nIndividuals by class:")
    for cls, count in sorted(type_counts.items()):
        print(f"  {cls}: {count}")

    print("\nInformation loss analysis:")
    loss_items = []
    for key, agent in parser.agents.items():
        if not agent.llm:
            loss_items.append(f"  Agent '{agent.role}': useLanguageModel NOT populated")

    if not loss_items:
        print("  No information loss detected for populated constructs.")
    else:
        for item in loss_items:
            print(item)

    # Dynamics check
    used_predicates = {str(p) for _, p, _ in graph}
    all_ontology_properties = [
        "agentPrompt",
        "agentResourceUsage",
        "agentToolUsage",
        "bindsMemory",
        "containsAgent",
        "containsOrchestration",
        "containsResource",
        "containsTeam",
        "contributesToGoal",
        "contributesToObjective",
        "dependsOn",
        "employsCoordinationPattern",
        "employsReasoningPattern",
        "hasAgentCapability",
        "hasAgentConfig",
        "hasAgentGoal",
        "hasAgentMember",
        "hasAssociatedTask",
        "hasCapability",
        "hasConfig",
        "hasEnvironmentConfig",
        "hasGoal",
        "hasGuardrail",
        "hasHumanCheckpoint",
        "hasKnowledge",
        "hasMemoryBinding",
        "hasObjective",
        "hasOutputSchema",
        "hasRelatedPattern",
        "hasSubCondition",
        "hasSubPattern",
        "hasSystemConfig",
        "hasTeamGoal",
        "hasTeamMemoryBinding",
        "hasTerminationCondition",
        "hasToolConfig",
        "hasWorkflowPattern",
        "hasWorkflowStep",
        "humanParticipatedIn",
        "interactsWith",
        "memoryBoundTo",
        "nextPattern",
        "nextStep",
        "operatesIn",
        "orchestratesTeam",
        "performedBy",
        "performedByAgent",
        "producedResource",
        "relatedStep",
        "requiresCapability",
        "requiresResource",
        "resourceUsage",
        "taskPrompt",
        "taskToolUsage",
        "toolUsage",
        "useLanguageModel",
    ]
    agentoscin_ns = str(AGENTOSCIN)
    unexercised = [
        p
        for p in all_ontology_properties
        if f"{agentoscin_ns}{p}" not in used_predicates
    ]

    if unexercised:
        print(
            f"\nObject properties not exercised ({len(unexercised)}/{len(all_ontology_properties)}):"
        )
        for prop in sorted(unexercised):
            print(f"  {prop}")
