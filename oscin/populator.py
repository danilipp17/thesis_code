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
from typing import Optional

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
            uri = self.EX[f"Tool_{self._safe_id(tool.class_name)}"]
            self.tool_uris[key] = uri

            # Mapping table 5: Tool instantiation → Tool individual
            self.g.add((uri, RDF.type, AGENTOSCIN.Tool))

            # Mapping table 5: Tool class name → dcterms:title
            self.g.add((uri, DCTERMS_TITLE, Literal(tool.name, datatype=XSD.string)))

            # Mapping table 5: Tool class docstring → dcterms:description
            self.g.add((uri, DCTERMS_DESCRIPTION, Literal(tool.description, datatype=XSD.string)))

            # Mapping table 5: BaseTool.args_schema → hasInputSchema
            self.g.add((uri, AGENTOSCIN.hasInputSchema, Literal(tool.args_schema_json, datatype=XSD.string)))

            # Mapping table 5: BaseTool._run → hasImplementationReference
            self.g.add((uri, AGENTOSCIN.hasImplementationReference, Literal(tool.implementation_ref, datatype=XSD.string)))

            log.info("  [Tool] %s → %s", tool.name, uri)

    # -----------------------------------------------------------
    # Agent Population
    # Mapping table Section 1
    # -----------------------------------------------------------

    def _populate_agents(self) -> None:
        for key, agent in self.parser.agents.items():
            uri = self.EX[f"Agent_{self._safe_id(key)}"]
            self.agent_uris[key] = uri

            # Mapping table 1: Agent class instantiation → LLMAgent individual
            self.g.add((uri, RDF.type, AGENTOSCIN.LLMAgent))

            # Mapping table 1: Agent.role → agentID
            self.g.add((uri, AGENTOSCIN.agentID, Literal(agent.role, datatype=XSD.string)))

            # Mapping table 1: Agent.role → agentRole (same value for CrewAI)
            self.g.add((uri, AGENTOSCIN.agentRole, Literal(agent.role, datatype=XSD.string)))

            # Mapping table 1: Agent (no explicit type) → agentType = "GeneralPurpose"
            self.g.add((uri, AGENTOSCIN.agentType, Literal("GeneralPurpose", datatype=XSD.string)))

            # Mapping table 1: Agent.reasoning → hasReasoningEnabled
            self.g.add((uri, AGENTOSCIN.hasReasoningEnabled, Literal(agent.reasoning, datatype=XSD.boolean)))

            # --- Goal ---
            # Mapping table 1: Agent.goal → hasAgentGoal → Goal individual
            if agent.goal:
                goal_uri = self.EX[f"Goal_{self._safe_id(key)}"]
                self.g.add((goal_uri, RDF.type, AGENTOSCIN.Goal))
                self.g.add((goal_uri, DCTERMS_DESCRIPTION, Literal(agent.goal, datatype=XSD.string)))
                self.g.add((uri, AGENTOSCIN.hasAgentGoal, goal_uri))

            # --- Agent Prompt ---
            # Mapping table 1: Agent.backstory → agentPrompt → Prompt.promptContext
            # Mapping table 1: Agent.role + Agent.goal → Prompt.promptInstruction
            prompt_uri = self.EX[f"AgentPrompt_{self._safe_id(key)}"]
            self.prompt_uris[f"agent_{key}"] = prompt_uri
            self.g.add((prompt_uri, RDF.type, AGENTOSCIN.Prompt))

            # Compose instruction from role + goal (mapping table row 6)
            instruction = f"{agent.role}: {agent.goal}" if agent.goal else agent.role
            self.g.add((prompt_uri, AGENTOSCIN.promptInstruction, Literal(instruction, datatype=XSD.string)))

            # Backstory → promptContext (mapping table row 5)
            if agent.backstory:
                self.g.add((prompt_uri, AGENTOSCIN.promptContext, Literal(agent.backstory, datatype=XSD.string)))

            # Mapping table 1: Always DualDirective for CrewAI agents
            self.g.add((prompt_uri, AGENTOSCIN.hasDirectiveFunction, Literal("DualDirective", datatype=XSD.string)))

            # Mapping table 1: Three source attributes
            self.g.add((prompt_uri, AGENTOSCIN.hasSourceAttribute, Literal("role, goal, backstory", datatype=XSD.string)))

            self.g.add((uri, AGENTOSCIN.agentPrompt, prompt_uri))

            # --- Tool bindings ---
            # Mapping table 1: Agent.tools → agentToolUsage → Tool
            for tool_class_name in agent.tools:
                if tool_class_name in self.tool_uris:
                    self.g.add((uri, AGENTOSCIN.agentToolUsage, self.tool_uris[tool_class_name]))

            # --- Language Model ---
            # Mapping table 1: Agent.llm → useLanguageModel → LanguageModel
            if agent.llm:
                lm_uri = self.EX[f"LM_{self._safe_id(agent.llm)}"]
                self.g.add((lm_uri, RDF.type, AGENTOSCIN.LanguageModel))
                self.g.add((lm_uri, DCTERMS_TITLE, Literal(agent.llm, datatype=XSD.string)))
                self.g.add((uri, AGENTOSCIN.useLanguageModel, lm_uri))

            # --- Agent-level config ---
            if agent.verbose is not None:
                self._add_config(uri, AGENTOSCIN.hasAgentConfig, "verbose", str(agent.verbose).lower())
            if agent.allow_delegation is not None:
                self._add_config(uri, AGENTOSCIN.hasAgentConfig, "allow_delegation", str(agent.allow_delegation).lower())

            # --- Reasoning ---
            # Mapping table 1: Agent.reasoning=True → employsReasoningPattern
            if agent.reasoning:
                rp_uri = self.EX["ReasoningPattern_Unspecified"]
                self.g.add((rp_uri, RDF.type, AGENTOSCIN.Unspecified))
                self.g.add((uri, AGENTOSCIN.employsReasoningPattern, rp_uri))
                self.g.add((uri, AGENTOSCIN.hasReasoningOrigin, Literal("FrameworkManaged", datatype=XSD.string)))
                if agent.max_reasoning_attempts is not None:
                    self.g.add((uri, AGENTOSCIN.hasMaxReasoningAttempts,
                                Literal(agent.max_reasoning_attempts, datatype=XSD.integer)))

            # --- Memory ---
            # Mapping table 1: Agent.memory=True → hasMemoryBinding → MemoryBinding
            if agent.memory:
                mb_uri = self.EX[f"MemoryBinding_Agent_{self._safe_id(key)}"]
                mem_uri = self.EX[f"Memory_Agent_{self._safe_id(key)}"]
                self.g.add((mb_uri, RDF.type, AGENTOSCIN.MemoryBinding))
                self.g.add((mb_uri, AGENTOSCIN.hasMemoryScope, Literal("AgentPrivate", datatype=XSD.string)))
                self.g.add((mb_uri, AGENTOSCIN.bindsMemory, mem_uri))
                self.g.add((mem_uri, RDF.type, AGENTOSCIN.Memory))
                self.g.add((mem_uri, AGENTOSCIN.hasPersistenceScope, Literal("Persistent", datatype=XSD.string)))
                self.g.add((uri, AGENTOSCIN.hasMemoryBinding, mb_uri))

            log.info("  [Agent] %s → %s", agent.role, uri)

    # -----------------------------------------------------------
    # Task Population
    # Mapping table Section 2
    # -----------------------------------------------------------

    def _populate_tasks(self) -> None:
        for key, task in self.parser.tasks.items():
            uri = self.EX[f"Task_{self._safe_id(key)}"]
            self.task_uris[key] = uri

            # Mapping table 2: Task class instantiation → Task individual
            self.g.add((uri, RDF.type, AGENTOSCIN.Task))

            # --- Expected Output ---
            # Mapping table 2: Task.expected_output → hasExpectedOutput
            if task.expected_output:
                self.g.add((uri, AGENTOSCIN.hasExpectedOutput, Literal(task.expected_output, datatype=XSD.string)))

            # --- Agent Assignment ---
            # Mapping table 2: Task.agent → performedByAgent → LLMAgent
            if task.agent_key and task.agent_key in self.agent_uris:
                self.g.add((uri, AGENTOSCIN.performedByAgent, self.agent_uris[task.agent_key]))
                # Mapping table 2: Task.agent present → ExplicitAssignment
                self.g.add((uri, AGENTOSCIN.hasDelegationStrategy, Literal("ExplicitAssignment", datatype=XSD.string)))
            else:
                # Mapping table 2: Task.agent absent → OrchestratorDelegated
                self.g.add((uri, AGENTOSCIN.hasDelegationStrategy, Literal("OrchestratorDelegated", datatype=XSD.string)))

            # --- Task Prompt ---
            # Mapping table 2: Task.description → taskPrompt → Prompt.promptInstruction
            task_prompt_uri = self.EX[f"TaskPrompt_{self._safe_id(key)}"]
            self.prompt_uris[f"task_{key}"] = task_prompt_uri
            self.g.add((task_prompt_uri, RDF.type, AGENTOSCIN.Prompt))

            if task.description:
                self.g.add((task_prompt_uri, AGENTOSCIN.promptInstruction,
                            Literal(task.description, datatype=XSD.string)))

            # Mapping table 2: Task.expected_output → Prompt.promptOutputIndicator
            if task.expected_output:
                self.g.add((task_prompt_uri, AGENTOSCIN.promptOutputIndicator,
                            Literal(task.expected_output, datatype=XSD.string)))

            # Mapping table 2: Source attributes
            self.g.add((task_prompt_uri, AGENTOSCIN.hasSourceAttribute,
                        Literal("description, expected_output", datatype=XSD.string)))

            self.g.add((uri, AGENTOSCIN.taskPrompt, task_prompt_uri))

            # --- Task-level tools ---
            # Mapping table 2: Task.tools → taskToolUsage → Tool
            for tool_name in task.tools:
                if tool_name in self.tool_uris:
                    self.g.add((uri, AGENTOSCIN.taskToolUsage, self.tool_uris[tool_name]))

            # --- Output Schema ---
            # Mapping table 2: Task.output_pydantic → hasOutputSchema → Schema
            if task.output_pydantic and task.output_pydantic in self.parser.pydantic_models:
                from oscin.utils import pydantic_fields_to_json_schema
                model = self.parser.pydantic_models[task.output_pydantic]
                schema_uri = self.EX[f"Schema_{self._safe_id(task.output_pydantic)}"]
                self.g.add((schema_uri, RDF.type, AGENTOSCIN.Schema))
                schema_json = pydantic_fields_to_json_schema(model.fields)
                self.g.add((schema_uri, AGENTOSCIN.hasSchemaDefinition,
                            Literal(schema_json, datatype=XSD.string)))
                self.g.add((uri, AGENTOSCIN.hasOutputSchema, schema_uri))

            # --- Dependencies ---
            # Mapping table 2: Task.context → dependsOn → Task
            for dep_key in task.context_tasks:
                if dep_key in self.task_uris:
                    self.g.add((uri, AGENTOSCIN.dependsOn, self.task_uris[dep_key]))
                    self.g.add((uri, AGENTOSCIN.hasDependencyType,
                                Literal("ContextProviding", datatype=XSD.string)))

            # --- Human Checkpoint ---
            # Mapping table 2: Task.human_input=True → hasHumanCheckpoint
            if task.human_input:
                hc_uri = self.EX[f"HumanCheckpoint_{self._safe_id(key)}"]
                self.g.add((hc_uri, RDF.type, AGENTOSCIN.HumanCheckpoint))
                self.g.add((hc_uri, AGENTOSCIN.hasCheckpointType, Literal("Review", datatype=XSD.string)))
                self.g.add((hc_uri, AGENTOSCIN.hasCheckpointPosition, Literal("AfterExecution", datatype=XSD.string)))
                self.g.add((hc_uri, AGENTOSCIN.isMandatory, Literal(True, datatype=XSD.boolean)))
                self.g.add((uri, AGENTOSCIN.hasHumanCheckpoint, hc_uri))

            log.info("  [Task] %s → %s", key, uri)

    # -----------------------------------------------------------
    # Team Population
    # Mapping table Section 3
    # -----------------------------------------------------------

    def _populate_teams(self) -> None:
        for key, team in self.parser.teams.items():
            uri = self.EX[f"Team_{self._safe_id(key)}"]
            self.team_uris[key] = uri

            # Mapping table 3: Crew class instantiation → Team individual
            self.g.add((uri, RDF.type, AGENTOSCIN.Team))
            self.g.add((uri, DCTERMS_TITLE, Literal(team.team_class_name, datatype=XSD.string)))

            # --- Agent Members ---
            # Mapping table 3: Crew.agents → hasAgentMember → LLMAgent
            for agent_key in team.agent_keys:
                if agent_key in self.agent_uris:
                    self.g.add((uri, AGENTOSCIN.hasAgentMember, self.agent_uris[agent_key]))

            # --- Coordination Pattern ---
            # Mapping table 3: Crew.process → employsCoordinationPattern
            # Uses the named individuals defined in agentoscin.ttl
            pattern_map = {
                "sequential": COORD_SEQUENTIAL,
                "hierarchical": AGENTOSCIN["HierachicalPattern"],
            }
            pattern_uri = pattern_map.get(team.process, COORD_CUSTOM)
            self.g.add((pattern_uri, RDF.type, AGENTOSCIN.CoordinationPattern))
            self.g.add((uri, AGENTOSCIN.employsCoordinationPattern, pattern_uri))

            # --- Termination ---
            # Mapping table 3: Crew implicit termination → TaskCompletionTermination
            term_uri = self.EX[f"Termination_{self._safe_id(key)}"]
            self.g.add((term_uri, RDF.type, AGENTOSCIN.TaskCompletionTermination))
            self.g.add((uri, AGENTOSCIN.hasTerminationCondition, term_uri))

            # --- Workflow Pattern ---
            # Mapping table 3: Crew.tasks → WorkflowPattern with WorkflowSteps
            wp_uri = self.EX[f"WorkflowPattern_{self._safe_id(key)}"]
            self.g.add((wp_uri, RDF.type, AGENTOSCIN.WorkflowPattern))
            self.g.add((uri, AGENTOSCIN.hasWorkflowPattern, wp_uri))

            prev_step_uri = None
            for idx, task_key in enumerate(team.task_keys):
                step_uri = self.EX[f"CrewStep_{self._safe_id(key)}_{self._safe_id(task_key)}"]

                # Determine step type based on position
                is_first = idx == 0
                is_last = idx == len(team.task_keys) - 1

                if is_first and is_last:
                    # Single-step crew: both StartStep and EndStep
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.StartStep))
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.EndStep))
                elif is_first:
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.StartStep))
                elif is_last:
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.EndStep))
                else:
                    self.g.add((step_uri, RDF.type, AGENTOSCIN.WorkflowStep))

                self.g.add((step_uri, DCTERMS_TITLE, Literal(task_key, datatype=XSD.string)))
                self.g.add((step_uri, AGENTOSCIN.stepOrder, Literal(idx + 1, datatype=XSD.integer)))

                # Link step to task
                if task_key in self.task_uris:
                    self.g.add((step_uri, AGENTOSCIN.hasAssociatedTask, self.task_uris[task_key]))

                # Link sequential steps
                if prev_step_uri is not None:
                    self.g.add((prev_step_uri, AGENTOSCIN.nextStep, step_uri))

                self.g.add((wp_uri, AGENTOSCIN.hasWorkflowStep, step_uri))
                prev_step_uri = step_uri

            # --- System Config ---
            if team.verbose:
                self._add_config(uri, AGENTOSCIN.hasSystemConfig, "verbose", "true")

            # --- Crew-level Memory ---
            # Mapping table 3: Crew.memory=True → hasTeamMemoryBinding
            if team.memory:
                mb_uri = self.EX[f"MemoryBinding_Team_{self._safe_id(key)}"]
                mem_uri = self.EX[f"Memory_Team_{self._safe_id(key)}"]
                self.g.add((mb_uri, RDF.type, AGENTOSCIN.MemoryBinding))
                self.g.add((mb_uri, AGENTOSCIN.hasMemoryScope, Literal("GroupShared", datatype=XSD.string)))
                self.g.add((mb_uri, AGENTOSCIN.bindsMemory, mem_uri))
                self.g.add((mem_uri, RDF.type, AGENTOSCIN.Memory))
                self.g.add((mem_uri, AGENTOSCIN.hasPersistenceScope, Literal("Persistent", datatype=XSD.string)))
                self.g.add((uri, AGENTOSCIN.hasTeamMemoryBinding, mb_uri))

            log.info("  [Team] %s → %s (process: %s)", key, uri, team.process)

    # -----------------------------------------------------------
    # Flow Population
    # Mapping table Section 4
    # -----------------------------------------------------------

    def _populate_flow(self) -> None:
        flow = self.parser.flow
        if not flow:
            log.info("  [Flow] No Flow class found — skipping.")
            return

        # --- Orchestration individual ---
        # Mapping table 4: Flow class definition → Orchestration
        orch_uri = self.EX[f"Orchestration_{self._safe_id(flow.class_name)}"]
        self.g.add((orch_uri, RDF.type, AGENTOSCIN.Orchestration))
        self.g.add((orch_uri, DCTERMS_TITLE, Literal(flow.class_name, datatype=XSD.string)))

        # Mapping table 4: Flow coordination pattern → Custom
        self.g.add((COORD_CUSTOM, RDF.type, AGENTOSCIN.CoordinationPattern))
        self.g.add((orch_uri, AGENTOSCIN.employsCoordinationPattern, COORD_CUSTOM))

        # --- Link to teams ---
        # Mapping table 4: Crew references inside Flow → orchestratesTeam
        for crew_ref in flow.crew_references:
            if crew_ref in self.team_uris:
                self.g.add((orch_uri, AGENTOSCIN.orchestratesTeam, self.team_uris[crew_ref]))

        # --- Flow Workflow Pattern ---
        wp_uri = self.EX[f"FlowWorkflowPattern_{self._safe_id(flow.class_name)}"]
        self.g.add((wp_uri, RDF.type, AGENTOSCIN.WorkflowPattern))
        self.g.add((orch_uri, AGENTOSCIN.hasWorkflowPattern, wp_uri))

        # --- Build step URIs and resolve routing ---
        step_uris: dict[str, URIRef] = {}
        step_order = 1

        # Phase 1: Create all step individuals
        for step in flow.steps:
            step_uri = self.EX[f"FlowStep_{self._safe_id(step.method_name)}"]
            step_uris[step.method_name] = step_uri

            # Mapping table 4: Determine step type from decorator
            if step.decorator_type == "start":
                self.g.add((step_uri, RDF.type, AGENTOSCIN.StartStep))
            elif step.decorator_type == "router":
                self.g.add((step_uri, RDF.type, AGENTOSCIN.ConditionalStep))
            elif step.decorator_type == "listen":
                # Listen steps with no outgoing connections are EndSteps.
                # We determine this in Phase 2 after resolving all edges.
                self.g.add((step_uri, RDF.type, AGENTOSCIN.WorkflowStep))
            else:
                self.g.add((step_uri, RDF.type, AGENTOSCIN.WorkflowStep))

            self.g.add((step_uri, DCTERMS_TITLE, Literal(step.method_name, datatype=XSD.string)))
            self.g.add((step_uri, AGENTOSCIN.stepOrder, Literal(step_order, datatype=XSD.integer)))
            self.g.add((wp_uri, AGENTOSCIN.hasWorkflowStep, step_uri))

            # Store routing logic for router steps
            if step.decorator_type == "router" and step.function_body:
                self.g.add((step_uri, AGENTOSCIN.hasRoutingLogic,
                            Literal(step.function_body, datatype=XSD.string)))

            step_order += 1

        # Phase 2: Resolve nextStep edges
        # Build a map from labels/method names to step URIs so that
        # @listen and @start decorator args can be resolved to targets.
        label_to_step: dict[str, URIRef] = {}
        for step in flow.steps:
            # A @listen("label") makes this step the target for that label
            if step.decorator_type == "listen":
                for arg in step.decorator_args:
                    label_to_step[arg] = step_uris[step.method_name]
            # A @start("label") also listens for that label
            if step.decorator_type == "start":
                for arg in step.decorator_args:
                    label_to_step[arg] = step_uris[step.method_name]
            # Methods can be referenced by name (for @router(method_ref))
            label_to_step[step.method_name] = step_uris[step.method_name]

        # Now resolve edges
        outgoing_edges: dict[str, list[str]] = {s.method_name: [] for s in flow.steps}

        for step in flow.steps:
            if step.decorator_type == "router":
                # Router return values map to @listen labels or @start labels
                for ret_val in step.return_values:
                    if ret_val in label_to_step:
                        self.g.add((step_uris[step.method_name], AGENTOSCIN.nextStep,
                                    label_to_step[ret_val]))
                        outgoing_edges[step.method_name].append(ret_val)

            elif step.decorator_type == "start":
                # @start methods flow to the next step — which is the
                # method that has @router(this_method) or @listen(this_method)
                for other in flow.steps:
                    if other.decorator_type in ("router", "listen"):
                        for arg in other.decorator_args:
                            if arg == step.method_name:
                                self.g.add((step_uris[step.method_name], AGENTOSCIN.nextStep,
                                            step_uris[other.method_name]))
                                outgoing_edges[step.method_name].append(other.method_name)

        # Phase 3: Reclassify listen steps with no outgoing edges as EndStep
        for step in flow.steps:
            if step.decorator_type == "listen" and not outgoing_edges[step.method_name]:
                step_uri = step_uris[step.method_name]
                # Remove generic WorkflowStep type and add EndStep
                self.g.remove((step_uri, RDF.type, AGENTOSCIN.WorkflowStep))
                self.g.add((step_uri, RDF.type, AGENTOSCIN.EndStep))

        log.info("  [Flow] %s → %s (%d steps, %d crew references)",
                 flow.class_name, orch_uri, len(flow.steps), len(flow.crew_references))

    # -----------------------------------------------------------
    # System-Level Population
    # Mapping table Section 6
    # -----------------------------------------------------------

    def _populate_system(self) -> None:
        """Create the AgenticSystem individual that contains everything."""
        sys_uri = self.EX[self._safe_id(self.system_name)]

        # Mapping table 6: Entire source file → AgenticSystem
        self.g.add((sys_uri, RDF.type, AGENTOSCIN.AgenticSystem))

        # Mapping table 6: System dcterms:title
        self.g.add((sys_uri, DCTERMS_TITLE, Literal(self.system_name, datatype=XSD.string)))

        # Mapping table 6: hasSourceFramework — from the parser
        self.g.add((sys_uri, AGENTOSCIN.hasSourceFramework,
                    Literal(self.parser.framework_name(), datatype=XSD.string)))

        # Mapping table 6: All Team instances → containsTeam
        for team_uri in self.team_uris.values():
            self.g.add((sys_uri, AGENTOSCIN.containsTeam, team_uri))

        # Mapping table 6: All Agent instances → containsAgent
        for agent_uri in self.agent_uris.values():
            self.g.add((sys_uri, AGENTOSCIN.containsAgent, agent_uri))

        # Mapping table 6: Flow instance → containsOrchestration
        if self.parser.flow:
            orch_uri = self.EX[f"Orchestration_{self._safe_id(self.parser.flow.class_name)}"]
            self.g.add((sys_uri, AGENTOSCIN.containsOrchestration, orch_uri))

        log.info("  [System] %s → %s", self.system_name, sys_uri)

    # -----------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------

    def _add_config(
        self, subject: URIRef, property_uri: URIRef, key: str, value: str
    ) -> None:
        """Create a Config individual and link it to the subject."""
        config_uri = self.EX[f"Config_{self._safe_id(key)}_{self._safe_id(str(subject).split('#')[-1])}"]
        self.g.add((config_uri, RDF.type, AGENTOSCIN.Config))
        self.g.add((config_uri, AGENTOSCIN.configKey, Literal(key, datatype=XSD.string)))
        self.g.add((config_uri, AGENTOSCIN.configValue, Literal(value, datatype=XSD.string)))
        self.g.add((subject, property_uri, config_uri))

    @staticmethod
    def _safe_id(name: str) -> str:
        """Convert a name to a URI-safe identifier."""
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")


# ===================================================================
# Validation Report (optional utility)
# ===================================================================

def print_validation_report(graph: Graph, parser: BaseSourceParser) -> None:
    """
    Print a summary of what was extracted and populated, highlighting
    any properties that could not be populated (information loss).

    The "unexercised properties" section is computed dynamically by
    comparing all object properties defined in the agentoscin namespace
    against the predicates actually used in the populated graph.
    """
    # Count individuals by type
    type_counts: dict[str, int] = {}
    for s, p, o in graph.triples((None, RDF.type, None)):
        type_name = str(o).split("/")[-1]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    print("\nIndividuals by class:")
    for cls, count in sorted(type_counts.items()):
        print(f"  {cls}: {count}")

    # Check for unpopulated properties (information loss)
    print("\nInformation loss analysis:")
    loss_items: list[str] = []

    for key, agent in parser.agents.items():
        if not agent.llm:
            loss_items.append(
                f"  Agent '{agent.role}': useLanguageModel NOT populated "
                f"(no explicit llm= parameter)"
            )

    if not loss_items:
        print("  No information loss detected for populated constructs.")
    else:
        for item in loss_items:
            print(item)

    # Dynamically compute unexercised properties
    # Collect all predicates actually used in the graph
    used_predicates = {str(p) for _, p, _ in graph}

    # Known agentoscin object properties that could be exercised
    # (derived from the ontology schema)
    agentoscin_ns = str(AGENTOSCIN)
    all_ontology_properties = [
        "agentPrompt", "agentResourceUsage", "agentToolUsage",
        "bindsMemory", "containsAgent", "containsOrchestration",
        "containsResource", "containsTeam", "contributesToGoal",
        "contributesToObjective", "dependsOn", "employsCoordinationPattern",
        "employsReasoningPattern", "hasAgentCapability", "hasAgentConfig",
        "hasAgentGoal", "hasAgentMember", "hasAssociatedTask",
        "hasCapability", "hasConfig", "hasEnvironmentConfig",
        "hasGoal", "hasGuardrail", "hasHumanCheckpoint",
        "hasKnowledge", "hasMemoryBinding", "hasObjective",
        "hasOutputSchema", "hasRelatedPattern", "hasSubCondition",
        "hasSubPattern", "hasSystemConfig", "hasTeamGoal",
        "hasTeamMemoryBinding", "hasTerminationCondition",
        "hasToolConfig", "hasWorkflowPattern", "hasWorkflowStep",
        "humanParticipatedIn", "interactsWith", "memoryBoundTo",
        "nextPattern", "nextStep", "operatesIn",
        "orchestratesTeam", "performedBy", "performedByAgent",
        "producedResource", "relatedStep", "requiresCapability",
        "requiresResource", "resourceUsage", "taskPrompt",
        "taskToolUsage", "toolUsage", "useLanguageModel",
    ]

    unexercised = [
        prop for prop in all_ontology_properties
        if f"{agentoscin_ns}{prop}" not in used_predicates
    ]

    if unexercised:
        print(f"\nObject properties not exercised ({len(unexercised)}/{len(all_ontology_properties)}):")
        for prop in sorted(unexercised):
            print(f"  {prop}")
    else:
        print("\nAll ontology object properties were exercised.")

    exercised_count = len(all_ontology_properties) - len(unexercised)
    total = len(all_ontology_properties)
    print(f"\nProperty coverage: {exercised_count}/{total} "
          f"({100 * exercised_count / total:.0f}%)")

