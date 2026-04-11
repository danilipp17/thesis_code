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
    AGENTOSCIN,
    COORD_CUSTOM,
    COORD_SEQUENTIAL,
    DCTERMS_DESCRIPTION,
    DCTERMS_REFERENCE,
    DCTERMS_TITLE,
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
        self.g.bind("agentoscin", AGENTOSCIN)
        self.g.bind("ex", self.EX)
        self.g.bind("owl", OWL)
        self.g.bind("rdfs", RDFS)

        # Declare this output graph as an OWL ontology
        onto_uri_str = str(self.EX).rstrip("#")
        onto_uri = URIRef(onto_uri_str)
        self.g.add((onto_uri, RDF.type, OWL.Ontology))

        # Explicitly import the base AgentOSCIN schema so Protégé maps
        # the predicates to ObjectProperties and DataProperties instead of Annotations
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
            uri = self._create_individual("Tool", tool.class_name, AGENTOSCIN.Tool)
            self.tool_uris[key] = uri

            # Mapping table 5 assertions
            self._add_str(uri, DCTERMS_TITLE, tool.name)
            self._add_str(uri, DCTERMS_DESCRIPTION, tool.description)
            self._add_str(uri, AGENTOSCIN.hasInputSchema, tool.args_schema_json)
            self._add_str(uri, AGENTOSCIN.hasImplementationReference, tool.implementation_ref)

            log.info("  [Tool] %s \u2192 %s", tool.name, uri)

    # -----------------------------------------------------------
    # Agent Population
    # Mapping table Section 1
    # -----------------------------------------------------------

    def _populate_agents(self) -> None:
        for key, agent in self.parser.agents.items():
            uri = self._create_individual("Agent", key, AGENTOSCIN.LLMAgent)
            self.agent_uris[key] = uri

            # Basic Agent props (Mapping table 1)
            self._add_str(uri, AGENTOSCIN.agentID, agent.role)
            self._add_str(uri, AGENTOSCIN.agentRole, agent.role)
            self._add_str(uri, AGENTOSCIN.agentType, "GeneralPurpose")
            self._add_bool(uri, AGENTOSCIN.hasReasoningEnabled, agent.reasoning)

            # --- Goal ---
            if agent.goal:
                goal_uri = self._create_individual("Goal", key, AGENTOSCIN.Goal)
                self._add_str(goal_uri, DCTERMS_DESCRIPTION, agent.goal)
                self.g.add((uri, AGENTOSCIN.hasAgentGoal, goal_uri))

            # --- Agent Prompt ---
            prompt_uri = self._create_individual("AgentPrompt", key, AGENTOSCIN.Prompt)
            self.prompt_uris[f"agent_{key}"] = prompt_uri
            
            # Compose instruction: role + goal
            instruction = f"{agent.role}: {agent.goal}" if agent.goal else agent.role
            self._add_str(prompt_uri, AGENTOSCIN.promptInstruction, instruction)
            self._add_str(prompt_uri, AGENTOSCIN.promptContext, agent.backstory)
            self._add_str(prompt_uri, AGENTOSCIN.hasDirectiveFunction, "DualDirective")
            self._add_str(prompt_uri, AGENTOSCIN.hasSourceAttribute, "role, goal, backstory")

            self.g.add((uri, AGENTOSCIN.agentPrompt, prompt_uri))

            # --- Tool bindings ---
            for tool_key in agent.tools:
                if tool_key in self.tool_uris:
                    self.g.add((uri, AGENTOSCIN.agentToolUsage, self.tool_uris[tool_key]))

            # --- Language Model ---
            if agent.llm:
                lm_uri = self._create_individual("LM", agent.llm, AGENTOSCIN.LanguageModel)
                self._add_str(lm_uri, DCTERMS_TITLE, agent.llm)
                self.g.add((uri, AGENTOSCIN.useLanguageModel, lm_uri))

            # --- Agent-level config ---
            if agent.verbose is not None:
                self._add_config(uri, AGENTOSCIN.hasAgentConfig, "verbose", str(agent.verbose).lower())
            if agent.allow_delegation is not None:
                self._add_config(uri, AGENTOSCIN.hasAgentConfig, "allow_delegation", str(agent.allow_delegation).lower())

            # --- Reasoning ---
            if agent.reasoning:
                rp_uri = self.EX["ReasoningPattern_Unspecified"]
                self.g.add((rp_uri, RDF.type, AGENTOSCIN.Unspecified))
                self.g.add((uri, AGENTOSCIN.employsReasoningPattern, rp_uri))
                self._add_str(uri, AGENTOSCIN.hasReasoningOrigin, "FrameworkManaged")
                if agent.max_reasoning_attempts is not None:
                    self._add_int(uri, AGENTOSCIN.hasMaxReasoningAttempts, agent.max_reasoning_attempts)

            # --- Memory ---
            if agent.memory:
                self._bind_memory(uri, key, "AgentPrivate")

            log.info("  [Agent] %s \u2192 %s", agent.role, uri)

    # -----------------------------------------------------------
    # Task Population
    # Mapping table Section 2
    # -----------------------------------------------------------

    def _populate_tasks(self) -> None:
        for key, task in self.parser.tasks.items():
            uri = self._create_individual("Task", key, AGENTOSCIN.Task)
            self.task_uris[key] = uri

            # Basic Task attributes
            self._add_str(uri, AGENTOSCIN.hasExpectedOutput, task.expected_output)

            # --- Agent Assignment ---
            if task.agent_key and task.agent_key in self.agent_uris:
                self.g.add((uri, AGENTOSCIN.performedByAgent, self.agent_uris[task.agent_key]))
                self._add_str(uri, AGENTOSCIN.hasDelegationStrategy, "ExplicitAssignment")
            else:
                self._add_str(uri, AGENTOSCIN.hasDelegationStrategy, "OrchestratorDelegated")

            # --- Task Prompt ---
            task_prompt_uri = self._create_individual("TaskPrompt", key, AGENTOSCIN.Prompt)
            self.prompt_uris[f"task_{key}"] = task_prompt_uri
            
            self._add_str(task_prompt_uri, AGENTOSCIN.promptInstruction, task.description)
            self._add_str(task_prompt_uri, AGENTOSCIN.promptOutputIndicator, task.expected_output)
            self._add_str(task_prompt_uri, AGENTOSCIN.hasSourceAttribute, "description, expected_output")

            self.g.add((uri, AGENTOSCIN.taskPrompt, task_prompt_uri))

            # --- Task-level tools ---
            for tool_name in task.tools:
                if tool_name in self.tool_uris:
                    self.g.add((uri, AGENTOSCIN.taskToolUsage, self.tool_uris[tool_name]))

            # --- Output Schema ---
            if task.output_pydantic and task.output_pydantic in self.parser.pydantic_models:
                model = self.parser.pydantic_models[task.output_pydantic]
                schema_uri = self._create_individual("Schema", task.output_pydantic, AGENTOSCIN.Schema)
                schema_json = pydantic_fields_to_json_schema(model.fields)
                self._add_str(schema_uri, AGENTOSCIN.hasSchemaDefinition, schema_json)
                self.g.add((uri, AGENTOSCIN.hasOutputSchema, schema_uri))

            # --- Dependencies ---
            for dep_key in task.context_tasks:
                if dep_key in self.task_uris:
                    self.g.add((uri, AGENTOSCIN.dependsOn, self.task_uris[dep_key]))
                    self._add_str(uri, AGENTOSCIN.hasDependencyType, "ContextProviding")

            # --- Human Checkpoint ---
            if task.human_input:
                hc_uri = self._create_individual("HumanCheckpoint", key, AGENTOSCIN.HumanCheckpoint)
                self._add_str(hc_uri, AGENTOSCIN.hasCheckpointType, "Review")
                self._add_str(hc_uri, AGENTOSCIN.hasCheckpointPosition, "AfterExecution")
                self._add_bool(hc_uri, AGENTOSCIN.isMandatory, True)
                self.g.add((uri, AGENTOSCIN.hasHumanCheckpoint, hc_uri))

            log.info("  [Task] %s \u2192 %s", key, uri)

    # -----------------------------------------------------------
    # Team Population
    # Mapping table Section 3
    # -----------------------------------------------------------

    def _populate_teams(self) -> None:
        for key, team in self.parser.teams.items():
            uri = self._create_individual("Team", key, AGENTOSCIN.Team)
            self.team_uris[key] = uri
            self._add_str(uri, DCTERMS_TITLE, team.team_class_name)

            # --- Agent Members ---
            for agent_key in team.agent_keys:
                if agent_key in self.agent_uris:
                    self.g.add((uri, AGENTOSCIN.hasAgentMember, self.agent_uris[agent_key]))

            # --- Coordination Pattern ---
            pattern_map = {
                "sequential": COORD_SEQUENTIAL,
                "hierarchical": AGENTOSCIN["HierachicalPattern"],
            }
            pattern_uri = pattern_map.get(team.process, COORD_CUSTOM)
            # Ensure type is set even if using predefined individual
            self.g.add((pattern_uri, RDF.type, AGENTOSCIN.CoordinationPattern))
            self.g.add((uri, AGENTOSCIN.employsCoordinationPattern, pattern_uri))

            # --- Termination ---
            term_uri = self._create_individual("Termination", key, AGENTOSCIN.TaskCompletionTermination)
            self.g.add((uri, AGENTOSCIN.hasTerminationCondition, term_uri))

            # --- Workflow Pattern ---
            wp_uri = self._create_individual("WorkflowPattern", key, AGENTOSCIN.WorkflowPattern)
            self.g.add((uri, AGENTOSCIN.hasWorkflowPattern, wp_uri))

            prev_step_uri = None
            for idx, task_key in enumerate(team.task_keys):
                step_uri = self.EX[f"CrewStep_{self._safe_id(key)}_{self._safe_id(task_key)}"]
                
                # Determine type
                is_first = idx == 0
                is_last = idx == len(team.task_keys) - 1
                if is_first and is_last:
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.StartStep))
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.EndStep))
                elif is_first:
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.StartStep))
                elif is_last:
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.EndStep))
                else:
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.WorkflowStep))

                self._add_str(step_uri, DCTERMS_TITLE, task_key)
                self._add_int(step_uri, AGENTOSCIN.stepOrder, idx + 1)

                if task_key in self.task_uris:
                    self.g.add((step_uri, AGENTOSCIN.hasAssociatedTask, self.task_uris[task_key]))

                if prev_step_uri is not None:
                    self.g.add((prev_step_uri, AGENTOSCIN.nextStep, step_uri))

                self.g.add((wp_uri, AGENTOSCIN.hasWorkflowStep, step_uri))
                prev_step_uri = step_uri

            # --- Config & Memory ---
            if team.verbose:
                self._add_config(uri, AGENTOSCIN.hasSystemConfig, "verbose", "true")
            if team.memory:
                self._bind_memory(uri, key, "GroupShared")

            log.info("  [Team] %s \u2192 %s (process: %s)", key, uri, team.process)

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
                self.g.add((orch_uri, AGENTOSCIN.orchestratesTeam, self.team_uris[crew_ref]))

        wp_uri = self._create_individual("FlowWorkflowPattern", flow.class_name, AGENTOSCIN.WorkflowPattern)
        self.g.add((orch_uri, AGENTOSCIN.hasWorkflowPattern, wp_uri))

        step_uris, outgoing_edges = self._create_flow_steps(flow, wp_uri)
        self._resolve_flow_edges(flow, step_uris, outgoing_edges)

        log.info("  [Flow] %s \u2192 %s (%d steps, %d crew references)",
                 flow.class_name, orch_uri, len(flow.steps), len(flow.crew_references))

    def _setup_orchestration_metadata(self, flow) -> URIRef:
        uri = self._create_individual("Orchestration", flow.class_name, AGENTOSCIN.Orchestration)
        self._add_str(uri, DCTERMS_TITLE, flow.class_name)
        
        # Default for CrewAI Flow
        self.g.add((COORD_CUSTOM, RDF.type, AGENTOSCIN.CoordinationPattern))
        self.g.add((uri, AGENTOSCIN.employsCoordinationPattern, COORD_CUSTOM))
        return uri

    def _create_flow_steps(self, flow, wp_uri: URIRef) -> tuple[dict[str, URIRef], dict[str, list[str]]]:
        step_uris: dict[str, URIRef] = {}
        outgoing_edges: dict[str, list[str]] = {}

        for idx, step in enumerate(flow.steps):
            uri = self._create_individual("FlowStep", step.method_name, AGENTOSCIN.WorkflowStep)
            step_uris[step.method_name] = uri
            outgoing_edges[step.method_name] = []

            # Determine specific step types
            if step.decorator_type == "start":
                self.g.add((uri, RDF.type, AGENTOSCIN.StartStep))
            elif step.decorator_type == "router":
                self.g.add((uri, RDF.type, AGENTOSCIN.ConditionalStep))
                self._add_str(uri, AGENTOSCIN.hasRoutingLogic, step.function_body)

            self._add_str(uri, DCTERMS_TITLE, step.method_name)
            self._add_int(uri, AGENTOSCIN.stepOrder, idx + 1)
            self.g.add((wp_uri, AGENTOSCIN.hasWorkflowStep, uri))
        
        return step_uris, outgoing_edges

    def _resolve_flow_edges(self, flow, step_uris: dict[str, URIRef], outgoing_edges: dict[str, list[str]]) -> None:
        # Resolve target mapping: @listen("label") or method names
        label_map: dict[str, URIRef] = {}
        for step in flow.steps:
            label_map[step.method_name] = step_uris[step.method_name]
            if step.decorator_type in ("listen", "start"):
                for arg in step.decorator_args:
                    label_map[arg] = step_uris[step.method_name]

        # Connect edges
        for step in flow.steps:
            src_uri = step_uris[step.method_name]
            
            if step.decorator_type == "router":
                for ret_val in step.return_values:
                    if ret_val in label_map:
                        self.g.add((src_uri, AGENTOSCIN.nextStep, label_map[ret_val]))
                        outgoing_edges[step.method_name].append(ret_val)

            elif step.decorator_type == "start":
                for other in flow.steps:
                    if other.decorator_type in ("router", "listen"):
                        if any(arg == step.method_name for arg in other.decorator_args):
                            self.g.add((src_uri, AGENTOSCIN.nextStep, step_uris[other.method_name]))
                            outgoing_edges[step.method_name].append(other.method_name)

        # Reclassify dead-ends as EndSteps
        for step_name, edges in outgoing_edges.items():
            if not edges:
                uri = step_uris[step_name]
                # If it's a generic step or listen step, make it an EndStep
                self.g.remove((uri, RDF.type, AGENTOSCIN.WorkflowStep))
                self.g.add((uri, RDF.type, AGENTOSCIN.EndStep))

    # -----------------------------------------------------------
    # System-Level Population
    # Mapping table Section 6
    # -----------------------------------------------------------

    def _populate_system(self) -> None:
        sys_uri = self.EX[self._safe_id(self.system_name)]
        self.g.add((sys_uri, RDF.type, AGENTOSCIN.AgenticSystem))
        
        self._add_str(sys_uri, DCTERMS_TITLE, self.system_name)
        self._add_str(sys_uri, AGENTOSCIN.hasSourceFramework, self.parser.framework_name())

        # Link containers
        for team_uri in self.team_uris.values():
            self.g.add((sys_uri, AGENTOSCIN.containsTeam, team_uri))
        for agent_uri in self.agent_uris.values():
            self.g.add((sys_uri, AGENTOSCIN.containsAgent, agent_uri))
        
        if self.parser.flow:
            orch_uri = self.EX[f"Orchestration_{self._safe_id(self.parser.flow.class_name)}"]
            self.g.add((sys_uri, AGENTOSCIN.containsOrchestration, orch_uri))

        log.info("  [System] %s \u2192 %s", self.system_name, sys_uri)

    # -----------------------------------------------------------
    # Refined Helpers
    # -----------------------------------------------------------

    def _create_individual(self, prefix: str, key: str, owl_class: URIRef) -> URIRef:
        """Create a URI and declare its RDF:type."""
        uri = self.EX[f"{prefix}_{self._safe_id(key)}"]
        self.g.add((uri, RDF.type, owl_class))
        return uri

    def _bind_memory(self, parent_uri: URIRef, key: str, scope: str) -> None:
        """Standardized memory instantiation for Agents and Teams."""
        mb_uri = self._create_individual(f"MemoryBinding_{scope}", key, AGENTOSCIN.MemoryBinding)
        mem_uri = self._create_individual(f"Memory_{scope}", key, AGENTOSCIN.Memory)
        
        self._add_str(mb_uri, AGENTOSCIN.hasMemoryScope, scope)
        self._add_str(mem_uri, AGENTOSCIN.hasPersistenceScope, "Persistent")
        self.g.add((mb_uri, AGENTOSCIN.bindsMemory, mem_uri))
        
        prop = AGENTOSCIN.hasTeamMemoryBinding if scope == "GroupShared" else AGENTOSCIN.hasMemoryBinding
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

    def _add_config(self, subject: URIRef, property_uri: URIRef, key: str, value: str) -> None:
        c_uri = self.EX[f"Config_{self._safe_id(key)}_{self._safe_id(str(subject).split('#')[-1])}"]
        self.g.add((c_uri, RDF.type, AGENTOSCIN.Config))
        self._add_str(c_uri, AGENTOSCIN.configKey, key)
        self._add_str(c_uri, AGENTOSCIN.configValue, value)
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
        "agentPrompt", "agentResourceUsage", "agentToolUsage", "bindsMemory", "containsAgent", 
        "containsOrchestration", "containsResource", "containsTeam", "contributesToGoal", 
        "contributesToObjective", "dependsOn", "employsCoordinationPattern", "employsReasoningPattern", 
        "hasAgentCapability", "hasAgentConfig", "hasAgentGoal", "hasAgentMember", "hasAssociatedTask", 
        "hasCapability", "hasConfig", "hasEnvironmentConfig", "hasGoal", "hasGuardrail", 
        "hasHumanCheckpoint", "hasKnowledge", "hasMemoryBinding", "hasObjective", "hasOutputSchema", 
        "hasRelatedPattern", "hasSubCondition", "hasSubPattern", "hasSystemConfig", "hasTeamGoal", 
        "hasTeamMemoryBinding", "hasTerminationCondition", "hasToolConfig", "hasWorkflowPattern", 
        "hasWorkflowStep", "humanParticipatedIn", "interactsWith", "memoryBoundTo", "nextPattern", 
        "nextStep", "operatesIn", "orchestratesTeam", "performedBy", "performedByAgent", 
        "producedResource", "relatedStep", "requiresCapability", "requiresResource", "resourceUsage", 
        "taskPrompt", "taskToolUsage", "toolUsage", "useLanguageModel"
    ]
    agentoscin_ns = str(AGENTOSCIN)
    unexercised = [p for p in all_ontology_properties if f"{agentoscin_ns}{p}" not in used_predicates]

    if unexercised:
        print(f"\nObject properties not exercised ({len(unexercised)}/{len(all_ontology_properties)}):")
        for prop in sorted(unexercised):
            print(f"  {prop}")
