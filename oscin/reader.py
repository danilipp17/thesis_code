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
    AGENTOSCIN,
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

        self._log_summary()

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
            log.info("  [System] %s (framework: %s)", self.system_name, self.source_framework)

    # -----------------------------------------------------------
    # Tools
    # -----------------------------------------------------------

    def _read_tools(self) -> None:
        """Read all Tool individuals."""
        for tool_uri in self.g.subjects(RDF.type, AGENTOSCIN.Tool):
            # Skip LLMAgents that are also typed as Tool (via subclass)
            if (tool_uri, RDF.type, AGENTOSCIN.LLMAgent) in self.g:
                continue

            name = self._str_value(tool_uri, HAS_TITLE) or ""
            description = self._str_value(tool_uri, HAS_DESCRIPTION) or ""
            input_schema = self._str_value(tool_uri, AGENTOSCIN.hasInputSchema) or "{}"
            impl_ref = self._str_value(tool_uri, AGENTOSCIN.hasImplementationReference) or ""

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
        for agent_uri in self.g.subjects(RDF.type, AGENTOSCIN.LLMAgent):
            role = self._str_value(agent_uri, AGENTOSCIN.agentRole) or ""
            agent_id = self._str_value(agent_uri, AGENTOSCIN.agentID) or role

            # Goal — follow hasAgentGoal → Goal → dcterms:description
            goal = ""
            for goal_uri in self.g.objects(agent_uri, AGENTOSCIN.hasAgentGoal):
                goal = self._str_value(goal_uri, HAS_DESCRIPTION) or ""

            # Backstory — follow agentPrompt → Prompt → promptContext
            backstory = ""
            for prompt_uri in self.g.objects(agent_uri, AGENTOSCIN.agentPrompt):
                backstory = self._str_value(prompt_uri, AGENTOSCIN.promptContext) or ""

            # LLM — follow useLanguageModel → LanguageModel → dcterms:title
            llm = None
            for lm_uri in self.g.objects(agent_uri, AGENTOSCIN.useLanguageModel):
                llm = self._str_value(lm_uri, HAS_TITLE)

            # Tools — follow agentToolUsage → Tool URIs
            tool_keys = []
            for tool_uri in self.g.objects(agent_uri, AGENTOSCIN.agentToolUsage):
                tool_key = self._tool_uri_to_key.get(str(tool_uri))
                if tool_key:
                    tool_keys.append(tool_key)

            # Reasoning
            reasoning = self._bool_value(agent_uri, AGENTOSCIN.hasReasoningEnabled)
            max_reasoning = self._int_value(agent_uri, AGENTOSCIN.hasMaxReasoningAttempts)

            # Memory
            memory = bool(list(self.g.objects(agent_uri, AGENTOSCIN.hasMemoryBinding)))

            # Config — verbose, allow_delegation
            verbose = self._config_value(agent_uri, AGENTOSCIN.hasAgentConfig, "verbose")
            allow_deleg = self._config_value(agent_uri, AGENTOSCIN.hasAgentConfig, "allow_delegation")

            # Derive key from URI local name
            key = self._local_name(agent_uri).replace("Agent_", "")

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
            )
            self.agents[key] = agent
            self._agent_uri_to_key[str(agent_uri)] = key
            log.info("  [Agent] %s (key: %s)", role, key)

    # -----------------------------------------------------------
    # Tasks
    # -----------------------------------------------------------

    def _read_tasks(self) -> None:
        """Read all Task individuals."""
        for task_uri in self.g.subjects(RDF.type, AGENTOSCIN.Task):
            expected_output = self._str_value(task_uri, AGENTOSCIN.hasExpectedOutput) or ""

            # Agent assignment — follow performedByAgent → agent URI
            agent_key = None
            for agent_uri in self.g.objects(task_uri, AGENTOSCIN.performedByAgent):
                agent_key = self._agent_uri_to_key.get(str(agent_uri))

            # Description — follow taskPrompt → Prompt → promptInstruction
            description = ""
            for prompt_uri in self.g.objects(task_uri, AGENTOSCIN.taskPrompt):
                description = self._str_value(prompt_uri, AGENTOSCIN.promptInstruction) or ""

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
            human_input = bool(list(self.g.objects(task_uri, AGENTOSCIN.hasHumanCheckpoint)))

            # Output schema
            output_pydantic = None
            for schema_uri in self.g.objects(task_uri, AGENTOSCIN.hasOutputSchema):
                schema_def = self._str_value(schema_uri, AGENTOSCIN.hasSchemaDefinition)
                if schema_def:
                    output_pydantic = self._local_name(schema_uri).replace("Schema_", "")
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
                tools=task_tools,
                context_tasks=context_tasks,
                human_input=human_input,
            )
            self.tasks[key] = task
            self._task_uri_to_key[str(task_uri)] = key
            log.info("  [Task] %s (agent: %s)", key, agent_key or "none")

    # -----------------------------------------------------------
    # Teams
    # -----------------------------------------------------------

    def _read_teams(self) -> None:
        """Read all Team individuals."""
        for team_uri in self.g.subjects(RDF.type, AGENTOSCIN.Team):
            title = self._str_value(team_uri, HAS_TITLE) or ""

            # Agent members
            agent_keys = []
            for agent_uri in self.g.objects(team_uri, AGENTOSCIN.hasAgentMember):
                ak = self._agent_uri_to_key.get(str(agent_uri))
                if ak:
                    agent_keys.append(ak)

            # Coordination pattern → process
            process = "sequential"
            for pattern_uri in self.g.objects(team_uri, AGENTOSCIN.employsCoordinationPattern):
                pattern_local = self._local_name(pattern_uri)
                if "Hierachical" in pattern_local or "hierarchical" in pattern_local.lower():
                    process = "hierarchical"
                elif "Custom" in pattern_local:
                    process = "custom"

            # Workflow steps → task_keys (ordered by stepOrder)
            task_keys = []
            for wp_uri in self.g.objects(team_uri, AGENTOSCIN.hasWorkflowPattern):
                steps = self._read_workflow_steps(wp_uri)
                for step_name, step_task_key in steps:
                    if step_task_key:
                        task_keys.append(step_task_key)

            # Verbose config
            verbose = False
            for config_uri in self.g.objects(team_uri, AGENTOSCIN.hasSystemConfig):
                ck = self._str_value(config_uri, AGENTOSCIN.configKey)
                cv = self._str_value(config_uri, AGENTOSCIN.configValue)
                if ck == "verbose" and cv == "true":
                    verbose = True

            # Memory
            memory = bool(list(self.g.objects(team_uri, AGENTOSCIN.hasTeamMemoryBinding)))

            key = self._local_name(team_uri).replace("Team_", "")

            team = ExtractedTeam(
                team_class_name=title or key,
                agent_keys=agent_keys,
                task_keys=task_keys,
                process=process,
                verbose=verbose,
                memory=memory,
            )
            self.teams[key] = team
            self._team_uri_to_key[str(team_uri)] = key
            log.info("  [Team] %s (agents: %d, tasks: %d, process: %s)",
                     key, len(agent_keys), len(task_keys), process)

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

            # Workflow steps
            steps: list[ExtractedFlowStep] = []
            for wp_uri in self.g.objects(orch_uri, AGENTOSCIN.hasWorkflowPattern):
                steps = self._read_flow_steps(wp_uri)

            self.flow = ExtractedFlow(
                class_name=class_name,
                steps=steps,
                crew_references=crew_refs,
            )
            log.info("  [Flow] %s (%d steps, %d crew refs)",
                     class_name, len(steps), len(crew_refs))

    def _read_flow_steps(self, wp_uri: URIRef) -> list[ExtractedFlowStep]:
        """
        Read WorkflowStep individuals from a flow-level WorkflowPattern
        and convert them to ExtractedFlowStep.
        """
        raw_steps: list[tuple[int, str, str, str, list[str]]] = []
        # (order, method_name, decorator_type, routing_logic, next_step_names)

        step_uri_to_name: dict[str, str] = {}
        step_info: dict[str, dict] = {}

        # Phase 1: Collect step info
        for step_uri in self.g.objects(wp_uri, AGENTOSCIN.hasWorkflowStep):
            name = self._str_value(step_uri, HAS_TITLE) or self._local_name(step_uri)
            order = self._int_value(step_uri, AGENTOSCIN.stepOrder) or 0

            # Determine decorator type from RDF type
            is_start = (step_uri, RDF.type, AGENTOSCIN.StartStep) in self.g
            is_conditional = (step_uri, RDF.type, AGENTOSCIN.ConditionalStep) in self.g
            is_end = (step_uri, RDF.type, AGENTOSCIN.EndStep) in self.g

            if is_conditional:
                dec_type = "router"
            elif is_start:
                dec_type = "start"
            else:
                dec_type = "listen"

            routing_logic = ""
            if is_conditional:
                routing_logic = self._str_value(step_uri, AGENTOSCIN.hasRoutingLogic) or ""

            # Collect nextStep targets
            next_names = []
            for next_uri in self.g.objects(step_uri, AGENTOSCIN.nextStep):
                next_names.append(str(next_uri))

            step_uri_to_name[str(step_uri)] = name
            step_info[str(step_uri)] = {
                "order": order,
                "name": name,
                "dec_type": dec_type,
                "routing_logic": routing_logic,
                "next_uris": next_names,
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
        # This helps determine decorator_args for @listen steps
        listened_by: dict[str, list[str]] = {}
        for uri_str, info in step_info.items():
            for next_name in info.get("next_names", []):
                listened_by.setdefault(next_name, []).append(info["name"])

        steps: list[ExtractedFlowStep] = []
        for uri_str in sorted_uris:
            info = step_info[uri_str]
            name = info["name"]

            # For @listen steps, decorator_args = the method names they listen to
            dec_args = []
            if info["dec_type"] == "listen":
                dec_args = listened_by.get(name, [])

            # For @router steps, return_values = the next step names
            return_values = []
            if info["dec_type"] == "router":
                return_values = info.get("next_names", [])

            step = ExtractedFlowStep(
                method_name=name,
                decorator_type=info["dec_type"],
                decorator_args=dec_args,
                return_values=return_values,
                function_body=info["routing_logic"],
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
        for step_uri in self.g.objects(wp_uri, AGENTOSCIN.hasWorkflowStep):
            order = self._int_value(step_uri, AGENTOSCIN.stepOrder) or 0
            title = self._str_value(step_uri, HAS_TITLE) or ""

            task_key = None
            for task_uri in self.g.objects(step_uri, AGENTOSCIN.hasAssociatedTask):
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
            ck = self._str_value(config_uri, AGENTOSCIN.configKey)
            if ck == config_key:
                return self._str_value(config_uri, AGENTOSCIN.configValue)
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
