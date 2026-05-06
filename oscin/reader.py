"""
reader.py
=========
Ontology Reader for the OSCIN reverse pipeline.

Reads a ``.ttl`` file containing agentoscin ontology individuals and
populates the shared intermediate dataclasses.  This is the exact
inverse of :mod:`oscin.populator`: it reads triples and produces the
same ``ExtractedAgent``, ``ExtractedTask``, etc. that a parser would.

Once populated, the reader's data can be fed to any code generator
to produce runnable framework source code.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from oscin.intermediate import (
    ExtractedAgent,
    ExtractedFlow,
    ExtractedFlowStep,
    ExtractedPydanticModel,
    ExtractedTask,
    ExtractedTeam,
    ExtractedTool,
)
from oscin.namespaces import (
    AGENTO,
    AGENTOSCIN,
    CALLS_CREW,
    COORD_CUSTOM,
    COORD_SEQUENTIAL,
    HAS_DESCRIPTION,
    HAS_TITLE,
)

log = logging.getLogger("oscin")


class OntologyReader:
    """
    Reads an agentoscin ``.ttl`` file and produces intermediate
    representations.

    The reader mirrors the structure of a ``BaseSourceParser``: after
    calling :meth:`read_all`, the same dictionaries are populated
    (``agents``, ``tasks``, ``tools``, ``teams``, ``flow``,
    ``pydantic_models``).

    Parameters
    ----------
    ttl_path : Path
        Path to the Turtle file to read.
    """

    def __init__(self, ttl_path: Path):
        self.ttl_path = ttl_path
        self.g = Graph()

        # Intermediate representation stores — same as BaseSourceParser
        self.agents: dict[str, ExtractedAgent] = {}
        self.tasks: dict[str, ExtractedTask] = {}
        self.tools: dict[str, ExtractedTool] = {}
        self.teams: dict[str, ExtractedTeam] = {}
        self.flow: Optional[ExtractedFlow] = None
        self.pydantic_models: dict[str, ExtractedPydanticModel] = {}

        # Internal lookup maps (URI → key)
        self._agent_uri_to_key: dict[str, str] = {}
        self._task_uri_to_key: dict[str, str] = {}
        self._tool_uri_to_key: dict[str, str] = {}
        self._team_uri_to_key: dict[str, str] = {}

        # Source framework detected from the AgenticSystem
        self.source_framework: str = "Unknown"
        self.system_name: str = ""

    # -----------------------------------------------------------
    # Public API
    # -----------------------------------------------------------

    def read_all(self) -> None:
        """
        Load the TTL file and extract all intermediate representations.

        Order mirrors the populator: tools → agents → tasks → teams → flow.
        """
        log.info("=" * 60)
        log.info("READING ONTOLOGY INSTANCE")
        log.info("TTL file: %s", self.ttl_path)
        log.info("=" * 60)

        self.g.parse(str(self.ttl_path), format="turtle")
        log.info("  Loaded %d triples", len(self.g))

        self._read_system()
        self._read_tools()
        self._read_agents()
        self._read_tasks()
        self._read_teams()
        self._read_flow()

        self._synthesize_state()

        self._log_summary()

    def _synthesize_state(self) -> None:
        """
        Synthesize a unified global state from all extracted tasks if none was explicitly defined.

        Only synthesizes for frameworks that use explicit state models
        (LangGraph). For CrewAI and AutoGen, state is managed internally
        by the framework and shouldn't be fabricated from task outputs.
        """
        if not self.flow:
            return

        # Only synthesize for flow-based frameworks that need explicit state
        stateful_frameworks = {"LangGraph"}
        if self.source_framework not in stateful_frameworks:
            return

        # If we already extracted explicit state fields, we respect them.
        if self.flow.state_fields:
            return

        synthesized_fields = {}
        for task_key, task in self.tasks.items():
            if task.expected_output:
                field_name = f"{task_key}_output"
                synthesized_fields[field_name] = "str"

        if not synthesized_fields:
            # Universal fallback for workflows with no expected output defined
            synthesized_fields["shared_context"] = "str"

        self.flow.state_fields = synthesized_fields
        log.info(
            "  [State] Synthesized %d state fields from tasks", len(synthesized_fields)
        )

    # -----------------------------------------------------------
    # System
    # -----------------------------------------------------------

    def _read_system(self) -> None:
        """Read the AgenticSystem individual."""
        for sys_uri in self.g.subjects(RDF.type, AGENTOSCIN.AgenticSystem):
            self.system_name = self._str_value(sys_uri, HAS_TITLE) or ""
            self.source_framework = (
                self._str_value(sys_uri, AGENTOSCIN.hasSourceFramework) or "Unknown"
            )
            log.info(
                "  [System] %s (framework: %s)", self.system_name, self.source_framework
            )

    # -----------------------------------------------------------
    # Tools
    # -----------------------------------------------------------

    def _read_tools(self) -> None:
        """Read all Tool individuals."""
        for tool_uri in self.g.subjects(RDF.type, AGENTO.Tool):
            # Skip LLMAgents that are also typed as Tool (via subclass)
            if (tool_uri, RDF.type, AGENTO.LLMAgent) in self.g:
                continue

            name = self._str_value(tool_uri, HAS_TITLE) or ""
            description = self._str_value(tool_uri, HAS_DESCRIPTION) or ""
            input_schema = self._str_value(tool_uri, AGENTOSCIN.hasInputSchema) or "{}"
            impl_ref = (
                self._str_value(tool_uri, AGENTOSCIN.hasImplementationReference) or ""
            )

            # Derive class_name from the URI local name
            class_name = self._local_name(tool_uri).replace("Tool_", "")
            key = class_name

            tool = ExtractedTool(
                class_name=class_name,
                name=name,
                description=description,
                args_schema_json=input_schema,
                implementation_ref=impl_ref,
            )
            self.tools[key] = tool
            self._tool_uri_to_key[str(tool_uri)] = key
            log.info("  [Tool] %s", name)

    # -----------------------------------------------------------
    # Agents
    # -----------------------------------------------------------

    def _read_agents(self) -> None:
        """Read all LLMAgent individuals."""
        for agent_uri in self.g.subjects(RDF.type, AGENTO.LLMAgent):
            role = self._str_value(agent_uri, AGENTO.agentRole) or ""
            # agentID is the stable source-level identifier (populator writes
            # the original key here). Do NOT fall back to role — role is
            # human-readable and may contain spaces, which would break URI
            # stability. Empty means "no explicit identifier in TTL".
            agent_id = self._str_value(agent_uri, AGENTO.agentID) or ""

            # Goal — follow hasAgentGoal → Goal → dcterms:description
            goal = ""
            for goal_uri in self.g.objects(agent_uri, AGENTO.hasAgentGoal):
                goal = self._str_value(goal_uri, HAS_DESCRIPTION) or ""

            # Backstory — follow agentPrompt → Prompt → promptContext
            backstory = ""
            for prompt_uri in self.g.objects(agent_uri, AGENTO.agentPrompt):
                backstory = self._str_value(prompt_uri, AGENTO.promptContext) or ""

            # LLM — follow useLanguageModel → LanguageModel → dcterms:title
            llm = None
            for lm_uri in self.g.objects(agent_uri, AGENTO.useLanguageModel):
                llm = self._str_value(lm_uri, HAS_TITLE)

            # Tools — follow agentToolUsage → Tool URIs
            tool_keys = []
            for tool_uri in self.g.objects(agent_uri, AGENTO.agentToolUsage):
                tool_key = self._tool_uri_to_key.get(str(tool_uri))
                if tool_key:
                    tool_keys.append(tool_key)

            # Reasoning
            reasoning = self._bool_value(agent_uri, AGENTOSCIN.hasReasoningEnabled)
            max_reasoning = self._int_value(
                agent_uri, AGENTOSCIN.hasMaxReasoningAttempts
            )
            reasoning_origin = (
                self._str_value(agent_uri, AGENTOSCIN.hasReasoningOrigin) or ""
            )

            # Reasoning pattern — follow employsReasoningPattern → individual
            # and recover the subclass name (ReAct, ChainOfThought, …) from
            # its rdf:type. Populator writes exactly one such triple.
            reasoning_pattern = ""
            _rp_type_map = {
                str(AGENTOSCIN.ReAct): "ReAct",
                str(AGENTOSCIN.ChainOfThought): "ChainOfThought",
                str(AGENTOSCIN.ReflectionLoop): "ReflectionLoop",
                str(AGENTOSCIN.TreeOfThoughts): "TreeOfThoughts",
            }
            for rp_uri in self.g.objects(
                agent_uri, AGENTOSCIN.employsReasoningPattern
            ):
                for rp_type in self.g.objects(rp_uri, RDF.type):
                    name = _rp_type_map.get(str(rp_type))
                    if name:
                        reasoning_pattern = name
                        break
                if reasoning_pattern:
                    break

            # Memory — also traverse MemoryBinding → bindsMemory to recover
            # the specific memory backend (e.g. "ChromaDBVectorMemory") and
            # persistence scope.
            memory = False
            memory_type = ""
            memory_persistence = ""
            for mb_uri in self.g.objects(agent_uri, AGENTOSCIN.hasMemoryBinding):
                memory = True
                for mem_uri in self.g.objects(mb_uri, AGENTOSCIN.bindsMemory):
                    memory_type = self._str_value(mem_uri, HAS_TITLE) or memory_type
                    memory_persistence = (
                        self._str_value(mem_uri, AGENTOSCIN.hasPersistenceScope)
                        or memory_persistence
                    )

            # Knowledge sources (via hasKnowledge → KnowledgeBase)
            knowledge_sources: list[str] = []
            for kb_uri in self.g.objects(agent_uri, AGENTO.hasKnowledge):
                kb_title = self._str_value(kb_uri, HAS_TITLE)
                if kb_title:
                    knowledge_sources.append(kb_title)

            # Agent type
            agent_type = self._str_value(agent_uri, AGENTOSCIN.agentType) or ""

            # Directive function — on the agent's prompt
            directive_function = ""
            prompt_source = ""
            for _prompt_uri in self.g.objects(agent_uri, AGENTO.agentPrompt):
                directive_function = self._str_value(_prompt_uri, AGENTOSCIN.hasDirectiveFunction) or ""
                prompt_source = self._str_value(_prompt_uri, AGENTOSCIN.hasSourceAttribute) or ""

            # Config — verbose, allow_delegation
            verbose = self._config_value(
                agent_uri, AGENTO.hasAgentConfig, "verbose"
            )
            allow_deleg = self._config_value(
                agent_uri, AGENTO.hasAgentConfig, "allow_delegation"
            )

            # Prefer agentID (source-level identifier written by populator) so
            # the original source key survives the round-trip. Fall back to the
            # URI local name for TTL graphs produced before this convention.
            key = agent_id or self._local_name(agent_uri).replace("Agent_", "")

            agent = ExtractedAgent(
                agent_key=key,
                role=role,
                goal=goal,
                backstory=backstory,
                llm=llm,
                tools=tool_keys,
                reasoning=reasoning,
                max_reasoning_attempts=max_reasoning,
                memory=memory,
                verbose=_str_to_bool(verbose) if verbose else None,
                allow_delegation=_str_to_bool(allow_deleg) if allow_deleg else None,
                knowledge_sources=knowledge_sources,
                agent_type=agent_type,
                directive_function=directive_function,
                prompt_source=prompt_source,
                reasoning_origin=reasoning_origin,
                reasoning_pattern=reasoning_pattern,
                memory_type=memory_type,
                memory_persistence=memory_persistence,
            )
            self.agents[key] = agent
            self._agent_uri_to_key[str(agent_uri)] = key
            log.info("  [Agent] %s (key: %s)", role, key)

    # -----------------------------------------------------------
    # Tasks
    # -----------------------------------------------------------

    def _read_tasks(self) -> None:
        """Read all Task individuals."""
        for task_uri in self.g.subjects(RDF.type, AGENTO.Task):
            expected_output = (
                self._str_value(task_uri, AGENTOSCIN.hasExpectedOutput) or ""
            )

            # Agent assignment — follow performedByAgent → agent URI
            agent_key = None
            for agent_uri in self.g.objects(task_uri, AGENTO.performedByAgent):
                agent_key = self._agent_uri_to_key.get(str(agent_uri))

            # Description — follow taskPrompt → Prompt → promptInstruction
            description = ""
            source_attribute = ""
            for prompt_uri in self.g.objects(task_uri, AGENTO.taskPrompt):
                description = (
                    self._str_value(prompt_uri, AGENTO.promptInstruction) or ""
                )
                source_attribute = (
                    self._str_value(prompt_uri, AGENTOSCIN.hasSourceAttribute) or ""
                )

            # Tools — follow taskToolUsage → Tool URIs
            task_tools = []
            for tool_uri in self.g.objects(task_uri, AGENTOSCIN.taskToolUsage):
                tool_key = self._tool_uri_to_key.get(str(tool_uri))
                if tool_key:
                    task_tools.append(tool_key)

            # Dependencies — follow dependsOn → Task URIs
            context_tasks = []
            for dep_uri in self.g.objects(task_uri, AGENTOSCIN.dependsOn):
                dep_key = self._task_uri_to_key.get(str(dep_uri))
                if dep_key:
                    context_tasks.append(dep_key)

            # Human checkpoint
            human_input = bool(
                list(self.g.objects(task_uri, AGENTOSCIN.hasHumanCheckpoint))
            )

            # Delegation strategy
            delegation_strategy = (
                self._str_value(task_uri, AGENTOSCIN.hasDelegationStrategy) or ""
            )

            # Guardrails — reconstruct "Type:detail" format written by
            # the populator (FunctionBased → hasValidationLogic, LLMBased →
            # dcterms:description, else raw description).
            guardrails: list[str] = []
            guardrail_max_retries: int | None = None
            for gr_uri in self.g.objects(task_uri, AGENTOSCIN.hasGuardrail):
                gr_type = self._str_value(gr_uri, AGENTOSCIN.hasGuardrailType) or ""
                if gr_type == "FunctionBased":
                    detail = (
                        self._str_value(gr_uri, AGENTOSCIN.hasValidationLogic) or ""
                    )
                    guardrails.append(f"FunctionBased:{detail}")
                elif gr_type == "LLMBased":
                    detail = self._str_value(gr_uri, HAS_DESCRIPTION) or ""
                    guardrails.append(f"LLMBased:{detail}")
                else:
                    detail = self._str_value(gr_uri, HAS_DESCRIPTION) or ""
                    if detail:
                        guardrails.append(detail)
                # hasMaxRetries is task-level in CrewAI source (one kwarg
                # applied across all guardrails). Read it off any guardrail
                # that carries it; last-writer-wins is safe because the
                # populator writes the same value to every sibling.
                mr = self._int_value(gr_uri, AGENTOSCIN.hasMaxRetries)
                if mr is not None:
                    guardrail_max_retries = mr

            # Output schema
            output_pydantic = None
            output_json = None
            for schema_uri in self.g.objects(task_uri, AGENTOSCIN.hasOutputSchema):
                source_attr = (
                    self._str_value(schema_uri, AGENTOSCIN.hasSourceAttribute) or ""
                )
                schema_def = self._str_value(schema_uri, AGENTOSCIN.hasSchemaDefinition)
                schema_title = self._str_value(schema_uri, HAS_TITLE)

                if source_attr == "output_json":
                    output_json = schema_title or self._local_name(schema_uri).replace(
                        "Schema_", ""
                    ).replace("_json", "")
                else:
                    # Default: output_pydantic (or legacy without source_attr)
                    output_pydantic = schema_title or self._local_name(schema_uri).replace(
                        "Schema_", ""
                    )
                    if schema_def:
                        # Store as a pydantic model
                        try:
                            schema_dict = json.loads(schema_def)
                            fields = {}
                            for fname, finfo in schema_dict.get("properties", {}).items():
                                fields[fname] = finfo.get("type", "str")
                            self.pydantic_models[output_pydantic] = ExtractedPydanticModel(
                                class_name=output_pydantic,
                                fields=fields,
                            )
                        except json.JSONDecodeError:
                            pass

            key = self._local_name(task_uri).replace("Task_", "")

            task = ExtractedTask(
                task_key=key,
                description=description,
                expected_output=expected_output,
                agent_key=agent_key,
                output_pydantic=output_pydantic,
                output_json=output_json,
                tools=task_tools,
                context_tasks=context_tasks,
                human_input=human_input,
                guardrails=guardrails,
                guardrail_max_retries=guardrail_max_retries,
                delegation_strategy=delegation_strategy,
                source_attribute=source_attribute,
            )
            self.tasks[key] = task
            self._task_uri_to_key[str(task_uri)] = key
            log.info("  [Task] %s (agent: %s)", key, agent_key or "none")

    # -----------------------------------------------------------
    # Teams
    # -----------------------------------------------------------

    def _read_teams(self) -> None:
        """Read all Team individuals."""
        for team_uri in self.g.subjects(RDF.type, AGENTO.Team):
            title = self._str_value(team_uri, HAS_TITLE) or ""

            # Agent members
            agent_keys = []
            for agent_uri in self.g.objects(team_uri, AGENTO.hasAgentMember):
                ak = self._agent_uri_to_key.get(str(agent_uri))
                if ak:
                    agent_keys.append(ak)

            # Coordination pattern → process
            process = "sequential"
            coordination_pattern = ""
            for pattern_uri in self.g.objects(
                team_uri, AGENTOSCIN.employsCoordinationPattern
            ):
                pattern_local = self._local_name(pattern_uri)
                coordination_pattern = pattern_local
                pattern_lower = pattern_local.lower()
                # Tolerant of the historical "Hierachical" misspelling that
                # may still exist in previously generated TTL files.
                if "hierarchical" in pattern_lower or "hierachical" in pattern_lower:
                    process = "hierarchical"
                elif "custom" in pattern_lower:
                    process = "custom"
                elif "sequential" in pattern_lower:
                    process = "sequential"

            # Workflow steps → task_keys (ordered by stepOrder)
            task_keys = []
            for wp_uri in self.g.objects(team_uri, AGENTO.hasWorkflowPattern):
                steps = self._read_workflow_steps(wp_uri)
                for step_name, step_task_key in steps:
                    if step_task_key:
                        task_keys.append(step_task_key)

            # Verbose config
            verbose = False
            for config_uri in self.g.objects(team_uri, AGENTO.hasSystemConfig):
                ck = self._str_value(config_uri, AGENTO.configKey)
                cv = self._str_value(config_uri, AGENTO.configValue)
                if ck == "verbose" and cv == "true":
                    verbose = True

            # Memory
            memory = bool(
                list(self.g.objects(team_uri, AGENTOSCIN.hasTeamMemoryBinding))
            )

            # Termination conditions: walk hasTerminationCondition and
            # rebuild the structured list the parser produced so that
            # EventBased triggers (TextMentionTermination("APPROVE")) and
            # MaxMessageTermination(n) survive the round-trip. Without this
            # the generator cannot re-emit hasTriggerExpression.
            max_turns = None
            termination_conditions: list[dict] = []
            for term_uri in self.g.objects(
                team_uri, AGENTOSCIN.hasTerminationCondition
            ):
                if (term_uri, RDF.type, AGENTOSCIN.TurnLimitTermination) in self.g:
                    mt = self._int_value(term_uri, AGENTOSCIN.hasMaxTurns)
                    if mt is not None:
                        max_turns = mt
                        termination_conditions.append(
                            {"type": "TurnLimit", "max_turns": mt}
                        )
                elif (
                    term_uri,
                    RDF.type,
                    AGENTOSCIN.EventBasedTermination,
                ) in self.g:
                    trigger = self._str_value(
                        term_uri, AGENTOSCIN.hasTriggerExpression
                    ) or ""
                    termination_conditions.append(
                        {"type": "EventBased", "trigger": trigger}
                    )
                elif (
                    term_uri,
                    RDF.type,
                    AGENTOSCIN.RoutingTermination,
                ) in self.g:
                    termination_conditions.append({"type": "Routing"})
                elif (
                    term_uri,
                    RDF.type,
                    AGENTOSCIN.CompositeTermination,
                ) in self.g:
                    operator = (
                        self._str_value(term_uri, AGENTOSCIN.hasOperator) or "OR"
                    )
                    sub_conditions: list[dict] = []
                    for sub_uri in self.g.objects(
                        term_uri, AGENTOSCIN.hasSubCondition
                    ):
                        if (
                            sub_uri,
                            RDF.type,
                            AGENTOSCIN.EventBasedTermination,
                        ) in self.g:
                            trigger = (
                                self._str_value(
                                    sub_uri, AGENTOSCIN.hasTriggerExpression
                                )
                                or ""
                            )
                            sub_conditions.append(
                                {"type": "EventBased", "trigger": trigger}
                            )
                        elif (
                            sub_uri,
                            RDF.type,
                            AGENTOSCIN.TurnLimitTermination,
                        ) in self.g:
                            mt = self._int_value(sub_uri, AGENTOSCIN.hasMaxTurns)
                            if mt is not None:
                                sub_conditions.append(
                                    {"type": "TurnLimit", "max_turns": mt}
                                )
                                # Promote to team-level so the generator can
                                # emit the MaxMessageTermination call.
                                if max_turns is None:
                                    max_turns = mt
                    termination_conditions.append(
                        {
                            "type": "Composite",
                            "operator": operator,
                            "conditions": sub_conditions,
                        }
                    )

            # Knowledge sources attached at team level
            team_knowledge: list[str] = []
            for kb_uri in self.g.objects(team_uri, AGENTO.hasKnowledge):
                kb_title = self._str_value(kb_uri, HAS_TITLE)
                if kb_title:
                    team_knowledge.append(kb_title)

            key = self._local_name(team_uri).replace("Team_", "")

            team = ExtractedTeam(
                team_class_name=title or key,
                agent_keys=agent_keys,
                task_keys=task_keys,
                process=process,
                verbose=verbose,
                memory=memory,
                max_turns=max_turns,
                knowledge_sources=team_knowledge,
                coordination_pattern=coordination_pattern,
                termination_conditions=termination_conditions,
            )
            self.teams[key] = team
            self._team_uri_to_key[str(team_uri)] = key
            log.info(
                "  [Team] %s (agents: %d, tasks: %d, process: %s)",
                key,
                len(agent_keys),
                len(task_keys),
                process,
            )

    # -----------------------------------------------------------
    # Flow / Orchestration
    # -----------------------------------------------------------

    def _read_flow(self) -> None:
        """Read the Orchestration individual and its workflow steps."""
        for orch_uri in self.g.subjects(RDF.type, AGENTOSCIN.Orchestration):
            class_name = self._str_value(orch_uri, HAS_TITLE) or "Flow"

            # Crew references
            crew_refs = []
            for team_uri in self.g.objects(orch_uri, AGENTOSCIN.orchestratesTeam):
                tk = self._team_uri_to_key.get(str(team_uri))
                if tk:
                    crew_refs.append(tk)

            # State schema (e.g. LangGraph TypedDict fields)
            state_model = None
            state_fields: dict[str, str] = {}
            for schema_uri in self.g.objects(orch_uri, AGENTOSCIN.hasOutputSchema):
                if (schema_uri, RDF.type, AGENTOSCIN.Schema) in self.g:
                    state_model = self._str_value(schema_uri, HAS_TITLE)
                    schema_def = self._str_value(
                        schema_uri, AGENTOSCIN.hasSchemaDefinition
                    )
                    if schema_def:
                        try:
                            state_fields = json.loads(schema_def)
                        except (json.JSONDecodeError, TypeError):
                            pass

            # Workflow steps
            steps: list[ExtractedFlowStep] = []
            for wp_uri in self.g.objects(orch_uri, AGENTO.hasWorkflowPattern):
                steps = self._read_flow_steps(wp_uri)

            # Fallback heuristic: if no step carries a calls_crew value
            # (e.g. TTL files produced before callsCrew was added), restore
            # the binding by assigning all non-router/non-conditional steps
            # to the first crew reference.
            if crew_refs:
                single_crew = crew_refs[0]
                for s in steps:
                    if s.step_type in ("start", "regular") and not s.function_body and not s.calls_crew:
                        s.calls_crew = single_crew

            self.flow = ExtractedFlow(
                class_name=class_name,
                state_model=state_model,
                steps=steps,
                crew_references=crew_refs,
                state_fields=state_fields,
            )
            log.info(
                "  [Flow] %s (%d steps, %d crew refs, state_fields: %s)",
                class_name,
                len(steps),
                len(crew_refs),
                list(state_fields.keys()) if state_fields else "none",
            )

    def _read_flow_steps(self, wp_uri: URIRef) -> list[ExtractedFlowStep]:
        """
        Read WorkflowStep individuals from a flow-level WorkflowPattern
        and convert them to ExtractedFlowStep.
        """
        raw_steps: list[tuple[int, str, str, str, list[str]]] = []
        # (order, method_name, step_type, routing_logic, next_step_names)

        step_uri_to_name: dict[str, str] = {}
        step_info: dict[str, dict] = {}

        # Phase 1: Collect step info
        for step_uri in self.g.objects(wp_uri, AGENTO.hasWorkflowStep):
            name = self._str_value(step_uri, HAS_TITLE) or self._local_name(step_uri)
            order = self._int_value(step_uri, AGENTO.stepOrder) or 0

            # Determine step type from RDF type
            is_start = (step_uri, RDF.type, AGENTO.StartStep) in self.g
            is_conditional = (step_uri, RDF.type, AGENTOSCIN.ConditionalStep) in self.g
            is_end = (step_uri, RDF.type, AGENTO.EndStep) in self.g

            # A step can be both start and conditional (LangGraph pattern:
            # entry node with conditional edges). EndStep is mutually
            # exclusive with StartStep — a start step is never just "end".
            if is_conditional and not is_start:
                step_type = "conditional"
            elif is_start:
                step_type = "start"
            elif is_end:
                step_type = "end"
            else:
                step_type = "regular"

            # Read routing logic for any conditional step (including start+conditional)
            routing_logic = ""
            if is_conditional:
                routing_logic = (
                    self._str_value(step_uri, AGENTOSCIN.hasRoutingLogic) or ""
                )

            # Read edge mapping (label → target node mapping)
            edge_mapping_json = (
                self._str_value(step_uri, AGENTOSCIN.hasEdgeMapping) or ""
            )
            edge_mapping: dict[str, str] = {}
            if edge_mapping_json:
                try:
                    edge_mapping = json.loads(edge_mapping_json)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Collect nextStep targets
            next_names = []
            for next_uri in self.g.objects(step_uri, AGENTO.nextStep):
                next_names.append(str(next_uri))

            # Original literal decorator arguments (e.g. CrewAI
            # @start("wait_next_run")) preserved by the populator. These
            # are restored ahead of the inferred dependency list.
            decorator_args: list[str] = []
            for lit in self.g.objects(step_uri, AGENTOSCIN.hasDecoratorArgument):
                if isinstance(lit, Literal):
                    decorator_args.append(str(lit))

            # Associated agent (e.g. LangGraph node → LLMAgent)
            associated_agent_key: Optional[str] = None
            for agent_uri in self.g.objects(step_uri, AGENTOSCIN.hasAssociatedAgent):
                key = self._agent_uri_to_key.get(str(agent_uri))
                if key:
                    associated_agent_key = key
                    break
            aggregation_combinator = (
                self._str_value(step_uri, AGENTOSCIN.hasAggregationCombinator) or ""
            )

            # Per-step crew binding (callsCrew)
            calls_crew = self._str_value(step_uri, CALLS_CREW)

            step_uri_to_name[str(step_uri)] = name
            step_info[str(step_uri)] = {
                "order": order,
                "name": name,
                "step_type": step_type,
                "routing_logic": routing_logic,
                "edge_mapping": edge_mapping,
                "next_uris": next_names,
                "decorator_args": decorator_args,
                "associated_agent_key": associated_agent_key,
                "aggregation_combinator": aggregation_combinator,
                "calls_crew": calls_crew,
            }

        # Phase 2: Resolve next_uris to method names
        for uri_str, info in step_info.items():
            resolved_nexts = []
            for next_uri_str in info["next_uris"]:
                next_name = step_uri_to_name.get(next_uri_str)
                if next_name:
                    resolved_nexts.append(next_name)
            info["next_names"] = resolved_nexts

        # Phase 3: Build ExtractedFlowStep objects
        # Sort by order
        sorted_uris = sorted(step_info.keys(), key=lambda u: step_info[u]["order"])

        # Build a reverse map: for each step, what listens to it?
        # This helps determine dependencies for regular steps
        listened_by: dict[str, list[str]] = {}
        for uri_str, info in step_info.items():
            for next_name in info.get("next_names", []):
                listened_by.setdefault(next_name, []).append(info["name"])

        steps: list[ExtractedFlowStep] = []
        for uri_str in sorted_uris:
            info = step_info[uri_str]
            name = info["name"]

            # Dependencies = literal decorator arguments preserved from the
            # source (e.g. CrewAI @start("wait_next_run")) followed by the
            # inferred predecessors from inverse nextStep edges. The literal
            # arguments come first so the generator emits them as-written.
            dec_args = list(info.get("decorator_args") or [])
            if info["step_type"] != "start":
                for pred in listened_by.get(name, []):
                    if pred not in dec_args:
                        dec_args.append(pred)

            # For conditional steps and start steps with routing logic,
            # return_values = the next step names or edge_mapping keys
            return_values = []
            if info["step_type"] == "conditional" or info["routing_logic"]:
                return_values = info.get("next_names", [])
                # If no resolved next_names but we have edge_mapping,
                # use the mapping keys as return values
                if not return_values and info.get("edge_mapping"):
                    return_values = list(info["edge_mapping"].keys())

            # Direct outgoing edges (non-conditional). Routing targets are
            # already carried by return_values/edge_mapping, so we only keep
            # plain nextStep targets for non-routing steps.
            outgoing = []
            if not (info["step_type"] == "conditional" or info["routing_logic"]):
                outgoing = list(info.get("next_names", []))

            step = ExtractedFlowStep(
                method_name=name,
                step_type=info["step_type"],
                dependencies=dec_args,
                return_values=return_values,
                function_body=info["routing_logic"],
                calls_crew=info.get("calls_crew"),
                edge_mapping=info.get("edge_mapping", {}),
                associated_agent_key=info.get("associated_agent_key") or None,
                aggregation_combinator=info.get("aggregation_combinator", ""),
                outgoing=outgoing,
            )
            steps.append(step)

        return steps

    # -----------------------------------------------------------
    # Helpers — Workflow Steps (Team-level)
    # -----------------------------------------------------------

    def _read_workflow_steps(self, wp_uri: URIRef) -> list[tuple[str, Optional[str]]]:
        """
        Read WorkflowStep individuals from a team-level WorkflowPattern.
        Returns sorted list of (step_title, associated_task_key).
        """
        steps: list[tuple[int, str, Optional[str]]] = []
        for step_uri in self.g.objects(wp_uri, AGENTO.hasWorkflowStep):
            order = self._int_value(step_uri, AGENTO.stepOrder) or 0
            title = self._str_value(step_uri, HAS_TITLE) or ""

            task_key = None
            for task_uri in self.g.objects(step_uri, AGENTO.hasAssociatedTask):
                task_key = self._task_uri_to_key.get(str(task_uri))
                if not task_key:
                    # Fallback: derive from URI
                    task_key = self._local_name(task_uri).replace("Task_", "")

            steps.append((order, title, task_key))

        steps.sort(key=lambda s: s[0])
        return [(s[1], s[2]) for s in steps]

    # -----------------------------------------------------------
    # Helpers — RDF Value Extraction
    # -----------------------------------------------------------

    def _str_value(self, subject: URIRef, predicate: URIRef) -> Optional[str]:
        """Get the first string value for a subject-predicate pair."""
        for obj in self.g.objects(subject, predicate):
            return str(obj)
        return None

    def _bool_value(self, subject: URIRef, predicate: URIRef) -> bool:
        """Get a boolean value, defaulting to False."""
        for obj in self.g.objects(subject, predicate):
            if isinstance(obj, Literal):
                return bool(obj.toPython())
            return str(obj).lower() == "true"
        return False

    def _int_value(self, subject: URIRef, predicate: URIRef) -> Optional[int]:
        """Get an integer value."""
        for obj in self.g.objects(subject, predicate):
            if isinstance(obj, Literal):
                try:
                    return int(obj.toPython())
                except (ValueError, TypeError):
                    return None
        return None

    def _config_value(
        self, subject: URIRef, config_property: URIRef, config_key: str
    ) -> Optional[str]:
        """
        Read a Config individual linked via config_property and return
        its configValue if configKey matches.
        """
        for config_uri in self.g.objects(subject, config_property):
            ck = self._str_value(config_uri, AGENTO.configKey)
            if ck == config_key:
                return self._str_value(config_uri, AGENTO.configValue)
        return None

    @staticmethod
    def _local_name(uri: URIRef) -> str:
        """Extract the local name (fragment or last path segment) from a URI."""
        s = str(uri)
        if "#" in s:
            return s.rsplit("#", 1)[1]
        return s.rsplit("/", 1)[-1]

    def _log_summary(self) -> None:
        log.info("")
        log.info("=" * 60)
        log.info("READING COMPLETE")
        log.info("  System:  %s", self.system_name)
        log.info("  Source:  %s", self.source_framework)
        log.info("  Agents:  %d", len(self.agents))
        log.info("  Tasks:   %d", len(self.tasks))
        log.info("  Tools:   %d", len(self.tools))
        log.info("  Teams:   %d", len(self.teams))
        log.info("  Flow:    %s", "yes" if self.flow else "no")
        log.info("  Models:  %d", len(self.pydantic_models))
        log.info("=" * 60)


# -----------------------------------------------------------
# Utility
# -----------------------------------------------------------


def _str_to_bool(s: str) -> bool:
    return s.lower() in ("true", "1", "yes")
