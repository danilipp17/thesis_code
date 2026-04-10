"""
crewai_ontology_extractor.py
=============================
Extraction and Ontology Population Pipeline for CrewAI Source Code

This script implements the extraction direction of the bidirectional
transformation method described in the thesis. It parses CrewAI source
code using Python's AST module and YAML parser, extracts agentic AI
constructs, and populates an OWL ontology using RDFLib.

The extraction follows the CrewAI → Ontology Mapping Table, with each
mapping rule referenced by its table section number.

Architecture
------------
The pipeline is structured into three layers, reflecting the OSCIN
method's separation of syntactic structure from semantic meaning:

  Layer 1 — Syntactic Parsing (AST + YAML)
      Reads source files and produces raw parse trees.

  Layer 2 — Intermediate Representation
      Dataclasses that capture extracted information in a
      framework-specific but structured form. This layer is the
      boundary between parsing and ontology population.

  Layer 3 — Ontology Population (RDFLib)
      Maps intermediate representations to OWL individuals and
      property assertions using the ontology namespace.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import ast
import json
import logging
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(message)s",
)
log = logging.getLogger("crewai_extractor")

# Ontology namespaces
AGENTO = Namespace("http://w3id.org/2025/agento/ontology#")
EX     = Namespace("http://example.org/email_flow#")
BEAM   = Namespace("http://w3id.org/2025/beam#")

# Source directory — configurable
SOURCE_DIR = Path(__file__).parent / "email-flow" / "source_files"


# ===================================================================
# LAYER 1 — INTERMEDIATE DATA MODEL
# ===================================================================
# These dataclasses serve as the structured boundary between raw AST
# parsing and ontology population. Each field is annotated with its
# source construct and the mapping table section it corresponds to.
# ===================================================================

@dataclass
class ExtractedAgent:
    """
    Intermediate representation of a CrewAI Agent.
    Mapping table: Section 1 (Agent Mapping).
    """
    # Identity — from YAML role field or Python config key
    agent_key: str              # YAML key, e.g. "shakespearean_bard"
    role: str                   # YAML role → agentID and agentRole
    goal: str                   # YAML goal → hasAgentGoal
    backstory: str              # YAML backstory → agentPrompt.promptContext

    # Optional Python-level parameters (from Agent() constructor)
    llm: Optional[str] = None               # → useLanguageModel
    tools: list[str] = field(default_factory=list)  # → agentToolUsage
    reasoning: bool = False                  # → hasReasoningEnabled
    max_reasoning_attempts: Optional[int] = None  # → hasMaxReasoningAttempts
    memory: bool = False                     # → hasMemoryBinding
    verbose: Optional[bool] = None           # → hasAgentConfig
    allow_delegation: Optional[bool] = None  # → hasAgentConfig

    # Provenance
    source_file: str = ""


@dataclass
class ExtractedTask:
    """
    Intermediate representation of a CrewAI Task.
    Mapping table: Section 2 (Task Mapping).
    """
    task_key: str               # YAML key, e.g. "write_x_post"
    description: str            # YAML description → taskPrompt.promptInstruction
    expected_output: str        # YAML expected_output → hasExpectedOutput
    agent_key: Optional[str] = None  # YAML agent → performedByAgent

    # Optional Python-level parameters
    output_pydantic: Optional[str] = None    # Class name → hasOutputSchema
    output_json: Optional[str] = None        # → hasOutputSchema
    tools: list[str] = field(default_factory=list)  # → taskToolUsage
    context_tasks: list[str] = field(default_factory=list)  # → dependsOn
    human_input: bool = False                # → hasHumanCheckpoint
    guardrails: list[str] = field(default_factory=list)  # → hasGuardrail

    # Provenance
    source_file: str = ""


@dataclass
class ExtractedTool:
    """
    Intermediate representation of a CrewAI Tool (BaseTool subclass).
    Mapping table: Section 5 (Tool Mapping).
    """
    class_name: str             # Python class name
    name: str                   # BaseTool.name → dcterms:title
    description: str            # BaseTool.description → dcterms:description
    args_schema_json: str       # Serialized JSON Schema → hasInputSchema
    implementation_ref: str     # Module path → hasImplementationReference
    source_file: str = ""


@dataclass
class ExtractedCrew:
    """
    Intermediate representation of a CrewAI Crew.
    Mapping table: Section 3 (Crew Mapping).
    """
    crew_class_name: str        # Python class name → dcterms:title
    agent_keys: list[str]       # References to agents → hasAgentMember
    task_keys: list[str]        # References to tasks → workflow steps
    process: str = "sequential" # "sequential" or "hierarchical"
    verbose: bool = False       # → hasSystemConfig
    memory: bool = False        # → hasTeamMemoryBinding
    manager_llm: Optional[str] = None       # → Manager agent
    manager_agent: Optional[str] = None     # → Manager agent
    source_file: str = ""


@dataclass
class ExtractedFlowStep:
    """
    Intermediate representation of a single Flow method.
    Mapping table: Section 4 (Flow Mapping).
    """
    method_name: str            # Python method name → step title
    decorator_type: str         # "start", "listen", or "router"
    decorator_args: list[str]   # Arguments to the decorator
    calls_crew: Optional[str] = None   # If method calls a Crew.kickoff()
    return_values: list[str] = field(default_factory=list)  # Router returns
    function_body: str = ""     # Serialized body → hasRoutingLogic (routers)


@dataclass
class ExtractedFlow:
    """
    Intermediate representation of a CrewAI Flow class.
    Mapping table: Section 4 (Flow Mapping).
    """
    class_name: str             # Python class name → dcterms:title
    state_model: Optional[str] = None  # Generic type arg (not modeled)
    steps: list[ExtractedFlowStep] = field(default_factory=list)
    crew_references: list[str] = field(default_factory=list)
    source_file: str = ""


@dataclass
class ExtractedPydanticModel:
    """
    Intermediate representation of a Pydantic BaseModel used for
    structured output (output_pydantic on Task).
    """
    class_name: str
    fields: dict[str, dict[str, str] | str]  # field_name → type info
    source_file: str = ""


# ===================================================================
# LAYER 2 — AST EXTRACTORS
# ===================================================================
# Each extractor function takes raw source code or file paths and
# returns instances of the intermediate dataclasses defined above.
# ===================================================================

class CrewAISourceParser:
    """
    Parses CrewAI source files and extracts intermediate representations.

    This class encapsulates all AST-level logic. It does NOT know about
    the ontology — it only produces ExtractedAgent, ExtractedTask, etc.
    objects. The ontology population layer consumes these objects.
    """

    def __init__(self, source_dir: Path):
        self.source_dir = source_dir
        self.agents: dict[str, ExtractedAgent] = {}
        self.tasks: dict[str, ExtractedTask] = {}
        self.tools: dict[str, ExtractedTool] = {}
        self.crews: dict[str, ExtractedCrew] = {}
        self.flow: Optional[ExtractedFlow] = None
        self.pydantic_models: dict[str, ExtractedPydanticModel] = {}

    # -----------------------------------------------------------
    # Public API
    # -----------------------------------------------------------

    def parse_all(self) -> None:
        """
        Execute the full extraction pipeline in dependency order.
        Tools and Pydantic models must be parsed before agents and
        tasks, because agents/tasks reference them.
        """
        log.info("=" * 60)
        log.info("STARTING CREWAI SOURCE CODE EXTRACTION")
        log.info("Source directory: %s", self.source_dir)
        log.info("=" * 60)

        # Step 1: Parse tools (no dependencies)
        self._parse_tools()

        # Step 2: Parse Pydantic models used as output schemas
        self._parse_pydantic_models()

        # Step 3: Parse crews (each crew references YAML configs)
        self._parse_crews()

        # Step 4: Parse the Flow class
        self._parse_flow()

        self._log_extraction_summary()

    # -----------------------------------------------------------
    # Step 1: Tool Extraction
    # Mapping table Section 5
    # -----------------------------------------------------------

    def _parse_tools(self) -> None:
        """
        Find all BaseTool subclasses and @tool-decorated functions.
        Extraction method: AST — detect BaseTool subclass.
        """
        tools_dir = self.source_dir / "tools"
        if not tools_dir.exists():
            log.warning("No tools/ directory found.")
            return

        for py_file in tools_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
            self._extract_basetool_subclasses(tree, py_file)

    def _extract_basetool_subclasses(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect classes inheriting from BaseTool and extract:
        - name (class attribute)       → dcterms:title
        - description (class attribute) → dcterms:description
        - args_schema (Pydantic model) → hasInputSchema
        - _run method                  → hasImplementationReference
        """
        # First pass: collect Pydantic input schema models defined
        # in the same file (they are args_schema targets).
        local_schemas: dict[str, dict[str, str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._inherits_from(node, "BaseModel"):
                    fields = self._extract_pydantic_fields(node)
                    local_schemas[node.name] = fields

        # Second pass: find BaseTool subclasses.
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not self._inherits_from(node, "BaseTool"):
                continue

            tool_name = ""
            tool_desc = ""
            schema_class_name = ""

            for item in node.body:
                # BaseTool class attributes are ast.AnnAssign nodes
                # e.g. name: str = "Character Counter Tool"
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    attr_name = item.target.id
                    attr_value = self._extract_constant_value(item.value)

                    if attr_name == "name" and attr_value:
                        tool_name = attr_value
                    elif attr_name == "description" and attr_value:
                        tool_desc = attr_value
                    elif attr_name == "args_schema" and isinstance(item.value, ast.Name):
                        schema_class_name = item.value.id

            # Serialize the args_schema Pydantic model to JSON Schema
            args_schema_json = "{}"
            if schema_class_name and schema_class_name in local_schemas:
                args_schema_json = self._pydantic_fields_to_json_schema(
                    local_schemas[schema_class_name]
                )

            # Build implementation reference from module path
            module_path = self._filepath_to_module(filepath)
            impl_ref = f"{module_path}.{node.name}._run"

            tool = ExtractedTool(
                class_name=node.name,
                name=tool_name or node.name,
                description=tool_desc,
                args_schema_json=args_schema_json,
                implementation_ref=impl_ref,
                source_file=str(filepath),
            )
            self.tools[node.name] = tool
            log.info(
                "  [Tool] Extracted '%s' from %s",
                tool.name, filepath.name,
            )

    # -----------------------------------------------------------
    # Step 2: Pydantic Model Extraction
    # (for Task.output_pydantic resolution)
    # -----------------------------------------------------------

    def _parse_pydantic_models(self) -> None:
        """
        Scan all Python files for Pydantic BaseModel subclasses.
        These are needed to resolve Task.output_pydantic references.
        """
        for py_file in self.source_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef) and self._inherits_from(node, "BaseModel"):
                    # Skip tool input schemas (already handled)
                    if node.name.endswith("Input"):
                        continue
                    fields = self._extract_pydantic_fields(node)
                    self.pydantic_models[node.name] = ExtractedPydanticModel(
                        class_name=node.name,
                        fields=fields,
                        source_file=str(py_file),
                    )

    # -----------------------------------------------------------
    # Step 3: Crew Extraction
    # Mapping table Sections 1, 2, 3
    # Each @CrewBase class is a Crew containing agents and tasks.
    # -----------------------------------------------------------

    def _parse_crews(self) -> None:
        """
        Find all @CrewBase-decorated classes. Each one defines a Crew
        with YAML-configured agents and tasks.
        """
        crews_dir = self.source_dir / "crews"
        if not crews_dir.exists():
            log.warning("No crews/ directory found.")
            return

        for py_file in crews_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            source = py_file.read_text()
            tree = ast.parse(source, filename=str(py_file))
            self._extract_crewbase_class(tree, py_file)

    def _extract_crewbase_class(self, tree: ast.Module, filepath: Path) -> None:
        """
        Parse a @CrewBase-decorated class to extract:
        - Agent definitions (from YAML config)
        - Task definitions (from YAML config + Python overrides)
        - Crew configuration (process type, verbose, memory)

        The CrewAI @CrewBase pattern works as follows:
        1. Class attributes agents_config and tasks_config point to
           YAML files relative to the class file.
        2. Methods decorated with @agent return Agent() instances
           whose config= parameter references a YAML key.
        3. Methods decorated with @task return Task() instances
           whose config= parameter references a YAML key.
        4. A method decorated with @crew returns a Crew() instance
           that wires agents and tasks together.
        """
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not self._has_decorator(node, "CrewBase"):
                continue

            crew_class_name = node.name
            log.info("  [Crew] Found @CrewBase class: %s", crew_class_name)

            # --- Locate YAML config paths ---
            agents_yaml_path = None
            tasks_yaml_path = None
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            val = self._extract_constant_value(item.value)
                            if target.id == "agents_config" and val:
                                agents_yaml_path = filepath.parent / val
                            elif target.id == "tasks_config" and val:
                                tasks_yaml_path = filepath.parent / val

            # --- Parse YAML configs ---
            agents_yaml = {}
            tasks_yaml = {}
            if agents_yaml_path and agents_yaml_path.exists():
                agents_yaml = yaml.safe_load(agents_yaml_path.read_text()) or {}
                log.info("    Loaded %d agent(s) from %s", len(agents_yaml), agents_yaml_path.name)
            if tasks_yaml_path and tasks_yaml_path.exists():
                tasks_yaml = yaml.safe_load(tasks_yaml_path.read_text()) or {}
                log.info("    Loaded %d task(s) from %s", len(tasks_yaml), tasks_yaml_path.name)

            # --- Extract agents from @agent methods ---
            agent_keys_in_crew = []
            for method in self._iter_methods(node):
                if not self._has_decorator(method, "agent"):
                    continue
                agent_key = method.name  # Method name = agent key
                agent_info = self._extract_agent_from_method(
                    method, agents_yaml, str(filepath)
                )
                if agent_info:
                    self.agents[agent_key] = agent_info
                    agent_keys_in_crew.append(agent_key)
                    log.info("    [Agent] '%s' (role: %s)", agent_key, agent_info.role)

            # --- Extract tasks from @task methods ---
            task_keys_in_crew = []
            for method in self._iter_methods(node):
                if not self._has_decorator(method, "task"):
                    continue
                task_key = method.name  # Method name = task key
                task_info = self._extract_task_from_method(
                    method, tasks_yaml, str(filepath)
                )
                if task_info:
                    self.tasks[task_key] = task_info
                    task_keys_in_crew.append(task_key)
                    log.info("    [Task] '%s' (agent: %s)", task_key, task_info.agent_key)

            # --- Extract Crew() configuration from @crew method ---
            crew_info = self._extract_crew_config(
                node, crew_class_name, agent_keys_in_crew,
                task_keys_in_crew, str(filepath)
            )
            self.crews[crew_class_name] = crew_info

    def _extract_agent_from_method(
        self,
        method: ast.FunctionDef,
        agents_yaml: dict,
        source_file: str,
    ) -> Optional[ExtractedAgent]:
        """
        Extract agent definition from an @agent method.

        Mapping table Section 1:
        - Agent.role       → agentID, agentRole
        - Agent.goal       → hasAgentGoal → Goal individual
        - Agent.backstory  → agentPrompt → Prompt.promptContext
        - Agent.tools      → agentToolUsage → Tool
        - Agent.llm        → useLanguageModel
        """
        # Find the Agent() call in the method body
        agent_call = self._find_call_in_method(method, "Agent")
        if not agent_call:
            return None

        # Resolve YAML config key from config= parameter
        # Pattern: Agent(config=self.agents_config["key"], ...)
        yaml_key = self._resolve_config_key(agent_call)

        yaml_data = {}
        if yaml_key and yaml_key in agents_yaml:
            yaml_data = agents_yaml[yaml_key]
        elif method.name in agents_yaml:
            # Fallback: method name matches YAML key
            yaml_data = agents_yaml[method.name]

        # Extract YAML fields (strip trailing whitespace from YAML block scalars)
        role = self._clean_yaml_string(yaml_data.get("role", method.name))
        goal = self._clean_yaml_string(yaml_data.get("goal", ""))
        backstory = self._clean_yaml_string(yaml_data.get("backstory", ""))

        # Extract Python-level keyword arguments that override or
        # supplement the YAML config
        tools = self._extract_tool_references(agent_call)
        llm = self._extract_keyword_string(agent_call, "llm")
        verbose = self._extract_keyword_bool(agent_call, "verbose")
        allow_delegation = self._extract_keyword_bool(agent_call, "allow_delegation")
        reasoning = self._extract_keyword_bool(agent_call, "reasoning") or False
        max_reasoning = self._extract_keyword_int(agent_call, "max_reasoning_attempts")
        memory = self._extract_keyword_bool(agent_call, "memory") or False

        return ExtractedAgent(
            agent_key=method.name,
            role=role,
            goal=goal,
            backstory=backstory,
            llm=llm,
            tools=tools,
            reasoning=reasoning,
            max_reasoning_attempts=max_reasoning,
            memory=memory,
            verbose=verbose,
            allow_delegation=allow_delegation,
            source_file=source_file,
        )

    def _extract_task_from_method(
        self,
        method: ast.FunctionDef,
        tasks_yaml: dict,
        source_file: str,
    ) -> Optional[ExtractedTask]:
        """
        Extract task definition from a @task method.

        Mapping table Section 2:
        - Task.description     → taskPrompt → Prompt.promptInstruction
        - Task.expected_output → hasExpectedOutput AND promptOutputIndicator
        - Task.agent           → performedByAgent
        - Task.output_pydantic → hasOutputSchema
        - Task.tools           → taskToolUsage
        - Task.context         → dependsOn
        - Task.human_input     → hasHumanCheckpoint
        - Task.guardrail       → hasGuardrail
        """
        task_call = self._find_call_in_method(method, "Task")
        if not task_call:
            return None

        # Resolve YAML config key
        yaml_key = self._resolve_config_key(task_call)
        yaml_data = {}
        if yaml_key and yaml_key in tasks_yaml:
            yaml_data = tasks_yaml[yaml_key]
        elif method.name in tasks_yaml:
            yaml_data = tasks_yaml[method.name]

        description = self._clean_yaml_string(yaml_data.get("description", ""))
        expected_output = self._clean_yaml_string(yaml_data.get("expected_output", ""))
        agent_key = yaml_data.get("agent", None)

        # Python-level overrides
        output_pydantic = self._extract_keyword_name(task_call, "output_pydantic")
        output_json = self._extract_keyword_name(task_call, "output_json")
        tools = self._extract_tool_references(task_call)
        human_input = self._extract_keyword_bool(task_call, "human_input") or False

        # Context (task dependencies): context=[task_a, task_b]
        context_tasks = self._extract_keyword_name_list(task_call, "context")

        return ExtractedTask(
            task_key=method.name,
            description=description,
            expected_output=expected_output,
            agent_key=agent_key,
            output_pydantic=output_pydantic,
            output_json=output_json,
            tools=tools,
            context_tasks=context_tasks,
            human_input=human_input,
            source_file=source_file,
        )

    def _extract_crew_config(
        self,
        class_node: ast.ClassDef,
        crew_class_name: str,
        agent_keys: list[str],
        task_keys: list[str],
        source_file: str,
    ) -> ExtractedCrew:
        """
        Extract Crew() configuration from the @crew method.

        Mapping table Section 3:
        - Crew.process      → employsCoordinationPattern
        - Crew.verbose      → hasSystemConfig
        - Crew.memory       → hasTeamMemoryBinding
        - Crew.manager_llm  → Manager agent creation
        """
        process = "sequential"
        verbose = False
        memory = False
        manager_llm = None
        manager_agent = None

        for method in self._iter_methods(class_node):
            if not self._has_decorator(method, "crew"):
                continue

            crew_call = self._find_call_in_method(method, "Crew")
            if not crew_call:
                continue

            # Extract process type
            # Pattern: process=Process.sequential or process=Process.hierarchical
            process_kw = self._find_keyword(crew_call, "process")
            if process_kw and isinstance(process_kw.value, ast.Attribute):
                process = process_kw.value.attr  # "sequential" or "hierarchical"

            verbose = self._extract_keyword_bool(crew_call, "verbose") or False
            memory = self._extract_keyword_bool(crew_call, "memory") or False
            manager_llm = self._extract_keyword_string(crew_call, "manager_llm")
            manager_agent = self._extract_keyword_name(crew_call, "manager_agent")

        return ExtractedCrew(
            crew_class_name=crew_class_name,
            agent_keys=agent_keys,
            task_keys=task_keys,
            process=process,
            verbose=verbose,
            memory=memory,
            manager_llm=manager_llm,
            manager_agent=manager_agent,
            source_file=source_file,
        )

    # -----------------------------------------------------------
    # Step 4: Flow Extraction
    # Mapping table Section 4
    # -----------------------------------------------------------

    def _parse_flow(self) -> None:
        """
        Find the Flow class in main.py and extract its decorated methods.
        """
        main_py = self.source_dir / "main.py"
        if not main_py.exists():
            log.warning("No main.py found — skipping Flow extraction.")
            return

        source = main_py.read_text()
        tree = ast.parse(source, filename=str(main_py))

        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not self._inherits_from(node, "Flow"):
                continue

            flow_class_name = node.name
            log.info("  [Flow] Found Flow class: %s", flow_class_name)

            # Extract generic type argument: Flow[StateModel]
            state_model = None
            for base in node.bases:
                if isinstance(base, ast.Subscript) and isinstance(base.slice, ast.Name):
                    state_model = base.slice.id

            # Extract decorated methods
            steps = []
            crew_references = set()

            for method in self._iter_methods(node):
                step = self._extract_flow_step(method, source)
                if step:
                    steps.append(step)
                    if step.calls_crew:
                        crew_references.add(step.calls_crew)
                    log.info(
                        "    [FlowStep] @%s: %s%s",
                        step.decorator_type, step.method_name,
                        f" → calls {step.calls_crew}" if step.calls_crew else "",
                    )

            self.flow = ExtractedFlow(
                class_name=flow_class_name,
                state_model=state_model,
                steps=steps,
                crew_references=list(crew_references),
                source_file=str(main_py),
            )

    def _extract_flow_step(
        self, method: ast.FunctionDef, full_source: str
    ) -> Optional[ExtractedFlowStep]:
        """
        Extract a single Flow method decorated with @start, @listen,
        or @router.

        Mapping table Section 4:
        - @start()   → StartStep
        - @listen(x)  → WorkflowStep, x determines nextStep source
        - @router(x)  → ConditionalStep, return values → nextStep targets
        """
        decorator_type = None
        decorator_args: list[str] = []

        for deco in method.decorator_list:
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name):
                deco_name = deco.func.id
                if deco_name in ("start", "listen", "router"):
                    decorator_type = deco_name
                    # Extract arguments (string labels or method references)
                    for arg in deco.args:
                        if isinstance(arg, ast.Constant):
                            decorator_args.append(str(arg.value))
                        elif isinstance(arg, ast.Name):
                            decorator_args.append(arg.id)
            elif isinstance(deco, ast.Name):
                # Bare decorator without parentheses: @start
                if deco.id in ("start", "listen", "router"):
                    decorator_type = deco.id

        if not decorator_type:
            return None

        # Detect crew.kickoff() calls in the method body.
        # Pattern: SomeCrewClass().crew().kickoff(...)
        calls_crew = self._find_crew_kickoff_in_method(method)

        # For @router methods, extract return values
        return_values = []
        if decorator_type == "router":
            return_values = self._extract_return_values(method)

        # Serialize the function body for routing logic storage.
        # We capture the entire method body (all statements) so that
        # the routing logic is complete and can be interpreted by a
        # generator targeting a different framework.
        function_body = ""
        if decorator_type == "router":
            # Strategy: use source positions to extract the full body
            # from the first statement to the last statement.
            first_stmt = method.body[0]
            last_stmt = method.body[-1]
            if hasattr(first_stmt, "lineno") and hasattr(last_stmt, "end_lineno"):
                source_lines = full_source.splitlines()
                # AST line numbers are 1-indexed
                body_lines = source_lines[first_stmt.lineno - 1 : last_stmt.end_lineno]
                function_body = "\n".join(body_lines)

            if not function_body:
                # Fallback: reconstruct from AST unparse
                function_body = "\n".join(
                    ast.unparse(stmt) for stmt in method.body
                )

        return ExtractedFlowStep(
            method_name=method.name,
            decorator_type=decorator_type,
            decorator_args=decorator_args,
            calls_crew=calls_crew,
            return_values=return_values,
            function_body=function_body,
        )

    # -----------------------------------------------------------
    # AST Helper Methods
    # -----------------------------------------------------------

    @staticmethod
    def _inherits_from(class_node: ast.ClassDef, base_name: str) -> bool:
        """Check if a class inherits from a given base (by simple name)."""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == base_name:
                return True
            if isinstance(base, ast.Subscript):
                if isinstance(base.value, ast.Name) and base.value.id == base_name:
                    return True
            if isinstance(base, ast.Attribute) and base.attr == base_name:
                return True
        return False

    @staticmethod
    def _has_decorator(node: ast.AST, decorator_name: str) -> bool:
        """Check if a class or function has a given decorator."""
        if not hasattr(node, "decorator_list"):
            return False
        for deco in node.decorator_list:
            if isinstance(deco, ast.Name) and deco.id == decorator_name:
                return True
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name):
                if deco.func.id == decorator_name:
                    return True
        return False

    @staticmethod
    def _iter_methods(class_node: ast.ClassDef):
        """Yield all method definitions in a class."""
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield item

    @staticmethod
    def _find_call_in_method(
        method: ast.FunctionDef, func_name: str
    ) -> Optional[ast.Call]:
        """Find the first call to func_name() inside a method body."""
        for node in ast.walk(method):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == func_name:
                    return node
        return None

    @staticmethod
    def _find_keyword(call_node: ast.Call, keyword: str) -> Optional[ast.keyword]:
        """Find a keyword argument in a function call."""
        for kw in call_node.keywords:
            if kw.arg == keyword:
                return kw
        return None

    @staticmethod
    def _extract_constant_value(node: Optional[ast.expr]) -> Optional[str]:
        """Extract a string constant from an AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _extract_keyword_string(self, call: ast.Call, name: str) -> Optional[str]:
        """Extract a string keyword argument value."""
        kw = self._find_keyword(call, name)
        if kw:
            return self._extract_constant_value(kw.value)
        return None

    def _extract_keyword_bool(self, call: ast.Call, name: str) -> Optional[bool]:
        """Extract a boolean keyword argument value."""
        kw = self._find_keyword(call, name)
        if kw and isinstance(kw.value, ast.Constant):
            return bool(kw.value.value)
        return None

    def _extract_keyword_int(self, call: ast.Call, name: str) -> Optional[int]:
        """Extract an integer keyword argument value."""
        kw = self._find_keyword(call, name)
        if kw and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
            return kw.value.value
        return None

    def _extract_keyword_name(self, call: ast.Call, name: str) -> Optional[str]:
        """Extract a Name reference (variable/class name) from a keyword."""
        kw = self._find_keyword(call, name)
        if kw and isinstance(kw.value, ast.Name):
            return kw.value.id
        return None

    def _extract_keyword_name_list(self, call: ast.Call, name: str) -> list[str]:
        """Extract a list of Name references from a keyword argument."""
        kw = self._find_keyword(call, name)
        if kw and isinstance(kw.value, ast.List):
            return [
                elt.id for elt in kw.value.elts
                if isinstance(elt, ast.Name)
            ]
        return []

    @staticmethod
    def _resolve_config_key(call: ast.Call) -> Optional[str]:
        """
        Resolve the YAML config key from patterns like:
          config=self.agents_config["key"]
        Returns "key" or None.
        """
        for kw in call.keywords:
            if kw.arg == "config" and isinstance(kw.value, ast.Subscript):
                if isinstance(kw.value.slice, ast.Constant):
                    return str(kw.value.slice.value)
        return None

    @staticmethod
    def _extract_tool_references(call: ast.Call) -> list[str]:
        """
        Extract tool class names from tools=[ToolA(), ToolB()].
        Returns a list of class names.
        """
        tools = []
        for kw in call.keywords:
            if kw.arg == "tools" and isinstance(kw.value, ast.List):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name):
                        tools.append(elt.func.id)
                    elif isinstance(elt, ast.Name):
                        tools.append(elt.id)
        return tools

    @staticmethod
    def _extract_return_values(method: ast.FunctionDef) -> list[str]:
        """
        Extract all string return values from a method body.
        Used for @router methods to determine conditional branches.
        """
        values = []
        for node in ast.walk(method):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    values.append(node.value.value)
        return values

    def _find_crew_kickoff_in_method(self, method: ast.FunctionDef) -> Optional[str]:
        """
        Detect patterns like SomeCrewClass().crew().kickoff(...) and
        return the crew class name "SomeCrewClass".
        """
        for node in ast.walk(method):
            if not isinstance(node, ast.Call):
                continue
            # Look for .kickoff() or .kickoff_async()
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("kickoff", "kickoff_async"):
                    # Walk up the chain: x.crew().kickoff()
                    # The x might be SomeCrewClass()
                    inner = node.func.value
                    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                        if inner.func.attr == "crew":
                            # Now find the class instantiation
                            obj = inner.func.value
                            if isinstance(obj, ast.Call) and isinstance(obj.func, ast.Name):
                                return obj.func.id
        return None

    @staticmethod
    def _extract_pydantic_fields(class_node: ast.ClassDef) -> dict[str, dict[str, str]]:
        """
        Extract field names, type annotations and Field descriptions
        from a Pydantic model. Returns {field_name: {"type": ..., "description": ...}}.
        """
        fields = {}
        for item in class_node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                type_str = ast.unparse(item.annotation) if item.annotation else "Any"
                desc = ""
                # Check for Field(..., description="...") in the default value
                if isinstance(item.value, ast.Call):
                    for kw in item.value.keywords:
                        if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                            desc = str(kw.value.value)
                fields[item.target.id] = {"type": type_str, "description": desc}
        return fields

    @staticmethod
    def _pydantic_fields_to_json_schema(fields: dict[str, dict[str, str] | str]) -> str:
        """
        Convert extracted Pydantic field definitions to a JSON Schema string.
        Accepts both legacy format {name: type_str} and enriched format
        {name: {"type": type_str, "description": desc}}.
        """
        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "Optional[str]": "string",
            "Optional[int]": "integer",
            "Optional[float]": "number",
            "Optional[bool]": "boolean",
        }

        properties = {}
        required = []
        for name, field_info in fields.items():
            # Handle both dict and plain string formats
            if isinstance(field_info, dict):
                type_str = field_info.get("type", "str")
                desc = field_info.get("description", "")
            else:
                type_str = field_info
                desc = ""

            json_type = type_map.get(type_str, "string")
            prop: dict[str, Any] = {"type": json_type}
            if desc:
                prop["description"] = desc
            if type_str.startswith("Optional"):
                prop["nullable"] = True
            else:
                required.append(name)
            properties[name] = prop

        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }
        return json.dumps(schema, separators=(",", ":"))

    @staticmethod
    def _clean_yaml_string(value: Any) -> str:
        """Strip trailing whitespace and newlines from YAML block scalars."""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _filepath_to_module(filepath: Path) -> str:
        """Convert a file path to a dotted Python module path."""
        parts = filepath.with_suffix("").parts
        # Find the package root (heuristic: start from "tools" or "crews")
        for i, part in enumerate(parts):
            if part in ("tools", "crews", "src"):
                return ".".join(parts[i:])
        return ".".join(parts[-3:])

    # -----------------------------------------------------------
    # Summary
    # -----------------------------------------------------------

    def _log_extraction_summary(self) -> None:
        log.info("=" * 60)
        log.info("EXTRACTION SUMMARY")
        log.info("  Agents: %d", len(self.agents))
        log.info("  Tasks:  %d", len(self.tasks))
        log.info("  Tools:  %d", len(self.tools))
        log.info("  Crews:  %d", len(self.crews))
        log.info("  Flow:   %s", "yes" if self.flow else "no")
        log.info("  Pydantic models: %d", len(self.pydantic_models))
        log.info("=" * 60)


# ===================================================================
# LAYER 3 — ONTOLOGY POPULATION
# ===================================================================
# This class takes the extracted intermediate representations and
# creates OWL individuals with property assertions in an RDFLib graph.
# Every method references the specific mapping table row it implements.
# ===================================================================

class OntologyPopulator:
    """
    Populates an RDF/OWL graph from extracted CrewAI constructs.

    The population follows the ontology property specification
    (ontology_properties_md.pdf) and the CrewAI mapping table
    (crewai_mapping_table.md). Each method documents which mapping
    rule it implements.
    """

    def __init__(self, parser: CrewAISourceParser, system_name: str):
        self.parser = parser
        self.system_name = system_name

        self.g = Graph()
        self._bind_namespaces()

        # Track created URIs for cross-referencing
        self.agent_uris: dict[str, URIRef] = {}
        self.task_uris: dict[str, URIRef] = {}
        self.tool_uris: dict[str, URIRef] = {}
        self.crew_uris: dict[str, URIRef] = {}
        self.prompt_uris: dict[str, URIRef] = {}

    def _bind_namespaces(self) -> None:
        self.g.bind("agento", AGENTO)
        self.g.bind("ex", EX)
        self.g.bind("dcterms", DCTERMS)
        self.g.bind("owl", OWL)
        self.g.bind("rdfs", RDFS)
        self.g.bind("beam", BEAM)

    # -----------------------------------------------------------
    # Public API
    # -----------------------------------------------------------

    def populate(self) -> Graph:
        """
        Execute the full ontology population pipeline.
        Order matters: tools and agents before tasks,
        tasks before crews, crews before flow.
        """
        log.info("")
        log.info("=" * 60)
        log.info("STARTING ONTOLOGY POPULATION")
        log.info("=" * 60)

        self._populate_tools()
        self._populate_agents()
        self._populate_tasks()
        self._populate_crews()
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
            uri = EX[f"Tool_{self._safe_id(tool.class_name)}"]
            self.tool_uris[key] = uri

            # Mapping table 5: Tool instantiation → Tool individual
            self.g.add((uri, RDF.type, AGENTO.Tool))

            # Mapping table 5: Tool class name → dcterms:title
            self.g.add((uri, DCTERMS.title, Literal(tool.name, datatype=XSD.string)))

            # Mapping table 5: Tool class docstring → dcterms:description
            self.g.add((uri, DCTERMS.description, Literal(tool.description, datatype=XSD.string)))

            # Mapping table 5: BaseTool.args_schema → hasInputSchema
            self.g.add((uri, AGENTO.hasInputSchema, Literal(tool.args_schema_json, datatype=XSD.string)))

            # Mapping table 5: BaseTool._run → hasImplementationReference
            self.g.add((uri, AGENTO.hasImplementationReference, Literal(tool.implementation_ref, datatype=XSD.string)))

            log.info("  [Tool] %s → %s", tool.name, uri)

    # -----------------------------------------------------------
    # Agent Population
    # Mapping table Section 1
    # -----------------------------------------------------------

    def _populate_agents(self) -> None:
        for key, agent in self.parser.agents.items():
            uri = EX[f"Agent_{self._safe_id(key)}"]
            self.agent_uris[key] = uri

            # Mapping table 1: Agent class instantiation → LLMAgent individual
            self.g.add((uri, RDF.type, AGENTO.LLMAgent))

            # Mapping table 1: Agent.role → agentID
            self.g.add((uri, AGENTO.agentID, Literal(agent.role, datatype=XSD.string)))

            # Mapping table 1: Agent.role → agentRole (same value for CrewAI)
            self.g.add((uri, AGENTO.agentRole, Literal(agent.role, datatype=XSD.string)))

            # Mapping table 1: Agent (no explicit type) → agentType = "GeneralPurpose"
            self.g.add((uri, AGENTO.agentType, Literal("GeneralPurpose", datatype=XSD.string)))

            # Mapping table 1: Agent.reasoning → hasReasoningEnabled
            self.g.add((uri, AGENTO.hasReasoningEnabled, Literal(agent.reasoning, datatype=XSD.boolean)))

            # --- Goal ---
            # Mapping table 1: Agent.goal → hasAgentGoal → Goal individual
            if agent.goal:
                goal_uri = EX[f"Goal_{self._safe_id(key)}"]
                self.g.add((goal_uri, RDF.type, AGENTO.Goal))
                self.g.add((goal_uri, DCTERMS.description, Literal(agent.goal, datatype=XSD.string)))
                self.g.add((uri, AGENTO.hasAgentGoal, goal_uri))

            # --- Agent Prompt ---
            # Mapping table 1: Agent.backstory → agentPrompt → Prompt.promptContext
            # Mapping table 1: Agent.role + Agent.goal → Prompt.promptInstruction
            prompt_uri = EX[f"AgentPrompt_{self._safe_id(key)}"]
            self.prompt_uris[f"agent_{key}"] = prompt_uri
            self.g.add((prompt_uri, RDF.type, AGENTO.Prompt))

            # Compose instruction from role + goal (mapping table row 6)
            instruction = f"{agent.role}: {agent.goal}" if agent.goal else agent.role
            self.g.add((prompt_uri, AGENTO.promptInstruction, Literal(instruction, datatype=XSD.string)))

            # Backstory → promptContext (mapping table row 5)
            if agent.backstory:
                self.g.add((prompt_uri, AGENTO.promptContext, Literal(agent.backstory, datatype=XSD.string)))

            # Mapping table 1: Always DualDirective for CrewAI agents
            self.g.add((prompt_uri, AGENTO.hasDirectiveFunction, Literal("DualDirective", datatype=XSD.string)))

            # Mapping table 1: Three source attributes
            self.g.add((prompt_uri, AGENTO.hasSourceAttribute, Literal("role, goal, backstory", datatype=XSD.string)))

            self.g.add((uri, AGENTO.agentPrompt, prompt_uri))

            # --- Tool bindings ---
            # Mapping table 1: Agent.tools → agentToolUsage → Tool
            for tool_class_name in agent.tools:
                if tool_class_name in self.tool_uris:
                    self.g.add((uri, AGENTO.agentToolUsage, self.tool_uris[tool_class_name]))

            # --- Language Model ---
            # Mapping table 1: Agent.llm → useLanguageModel → LanguageModel
            if agent.llm:
                lm_uri = EX[f"LM_{self._safe_id(agent.llm)}"]
                self.g.add((lm_uri, RDF.type, AGENTO.LanguageModel))
                self.g.add((lm_uri, DCTERMS.title, Literal(agent.llm, datatype=XSD.string)))
                self.g.add((uri, AGENTO.useLanguageModel, lm_uri))

            # --- Agent-level config ---
            if agent.verbose is not None:
                self._add_config(uri, AGENTO.hasAgentConfig, "verbose", str(agent.verbose).lower())
            if agent.allow_delegation is not None:
                self._add_config(uri, AGENTO.hasAgentConfig, "allow_delegation", str(agent.allow_delegation).lower())

            # --- Reasoning ---
            # Mapping table 1: Agent.reasoning=True → employsReasoningPattern
            if agent.reasoning:
                rp_uri = EX["ReasoningPattern_Unspecified"]
                self.g.add((rp_uri, RDF.type, AGENTO.ReasoningPattern))
                self.g.add((uri, AGENTO.employsReasoningPattern, rp_uri))
                self.g.add((uri, AGENTO.hasReasoningOrigin, Literal("FrameworkManaged", datatype=XSD.string)))
                if agent.max_reasoning_attempts is not None:
                    self.g.add((uri, AGENTO.hasMaxReasoningAttempts,
                                Literal(agent.max_reasoning_attempts, datatype=XSD.integer)))

            # --- Memory ---
            # Mapping table 1: Agent.memory=True → hasMemoryBinding → MemoryBinding
            if agent.memory:
                mb_uri = EX[f"MemoryBinding_Agent_{self._safe_id(key)}"]
                mem_uri = EX[f"Memory_Agent_{self._safe_id(key)}"]
                self.g.add((mb_uri, RDF.type, AGENTO.MemoryBinding))
                self.g.add((mb_uri, AGENTO.hasMemoryScope, Literal("AgentPrivate", datatype=XSD.string)))
                self.g.add((mb_uri, AGENTO.bindsMemory, mem_uri))
                self.g.add((mem_uri, RDF.type, AGENTO.Memory))
                self.g.add((mem_uri, AGENTO.hasPersistenceScope, Literal("Persistent", datatype=XSD.string)))
                self.g.add((uri, AGENTO.hasMemoryBinding, mb_uri))

            log.info("  [Agent] %s → %s", agent.role, uri)

    # -----------------------------------------------------------
    # Task Population
    # Mapping table Section 2
    # -----------------------------------------------------------

    def _populate_tasks(self) -> None:
        for key, task in self.parser.tasks.items():
            uri = EX[f"Task_{self._safe_id(key)}"]
            self.task_uris[key] = uri

            # Mapping table 2: Task class instantiation → Task individual
            self.g.add((uri, RDF.type, AGENTO.Task))

            # --- Expected Output ---
            # Mapping table 2: Task.expected_output → hasExpectedOutput
            if task.expected_output:
                self.g.add((uri, AGENTO.hasExpectedOutput, Literal(task.expected_output, datatype=XSD.string)))

            # --- Agent Assignment ---
            # Mapping table 2: Task.agent → performedByAgent → LLMAgent
            if task.agent_key and task.agent_key in self.agent_uris:
                self.g.add((uri, AGENTO.performedByAgent, self.agent_uris[task.agent_key]))
                # Mapping table 2: Task.agent present → ExplicitAssignment
                self.g.add((uri, AGENTO.hasDelegationStrategy, Literal("ExplicitAssignment", datatype=XSD.string)))
            else:
                # Mapping table 2: Task.agent absent → OrchestratorDelegated
                self.g.add((uri, AGENTO.hasDelegationStrategy, Literal("OrchestratorDelegated", datatype=XSD.string)))

            # --- Task Prompt ---
            # Mapping table 2: Task.description → taskPrompt → Prompt.promptInstruction
            task_prompt_uri = EX[f"TaskPrompt_{self._safe_id(key)}"]
            self.prompt_uris[f"task_{key}"] = task_prompt_uri
            self.g.add((task_prompt_uri, RDF.type, AGENTO.Prompt))

            if task.description:
                self.g.add((task_prompt_uri, AGENTO.promptInstruction,
                            Literal(task.description, datatype=XSD.string)))

            # Mapping table 2: Task.expected_output → Prompt.promptOutputIndicator
            if task.expected_output:
                self.g.add((task_prompt_uri, AGENTO.promptOutputIndicator,
                            Literal(task.expected_output, datatype=XSD.string)))

            # Mapping table 2: Source attributes
            self.g.add((task_prompt_uri, AGENTO.hasSourceAttribute,
                        Literal("description, expected_output", datatype=XSD.string)))

            self.g.add((uri, AGENTO.taskPrompt, task_prompt_uri))

            # --- Task-level tools ---
            # Mapping table 2: Task.tools → taskToolUsage → Tool
            for tool_name in task.tools:
                if tool_name in self.tool_uris:
                    self.g.add((uri, AGENTO.taskToolUsage, self.tool_uris[tool_name]))

            # --- Output Schema ---
            # Mapping table 2: Task.output_pydantic → hasOutputSchema → Schema
            if task.output_pydantic and task.output_pydantic in self.parser.pydantic_models:
                model = self.parser.pydantic_models[task.output_pydantic]
                schema_uri = EX[f"Schema_{self._safe_id(task.output_pydantic)}"]
                self.g.add((schema_uri, RDF.type, AGENTO.Schema))
                schema_json = CrewAISourceParser._pydantic_fields_to_json_schema(model.fields)
                self.g.add((schema_uri, AGENTO.hasSchemaDefinition,
                            Literal(schema_json, datatype=XSD.string)))
                self.g.add((uri, AGENTO.hasOutputSchema, schema_uri))

            # --- Dependencies ---
            # Mapping table 2: Task.context → dependsOn → Task
            for dep_key in task.context_tasks:
                if dep_key in self.task_uris:
                    self.g.add((uri, AGENTO.dependsOn, self.task_uris[dep_key]))
                    self.g.add((uri, AGENTO.hasDependencyType,
                                Literal("ContextProviding", datatype=XSD.string)))

            # --- Human Checkpoint ---
            # Mapping table 2: Task.human_input=True → hasHumanCheckpoint
            if task.human_input:
                hc_uri = EX[f"HumanCheckpoint_{self._safe_id(key)}"]
                self.g.add((hc_uri, RDF.type, AGENTO.HumanCheckpoint))
                self.g.add((hc_uri, AGENTO.hasCheckpointType, Literal("Review", datatype=XSD.string)))
                self.g.add((hc_uri, AGENTO.hasCheckpointPosition, Literal("AfterExecution", datatype=XSD.string)))
                self.g.add((hc_uri, AGENTO.isMandatory, Literal(True, datatype=XSD.boolean)))
                self.g.add((uri, AGENTO.hasHumanCheckpoint, hc_uri))

            log.info("  [Task] %s → %s", key, uri)

    # -----------------------------------------------------------
    # Crew Population
    # Mapping table Section 3
    # -----------------------------------------------------------

    def _populate_crews(self) -> None:
        for key, crew in self.parser.crews.items():
            uri = EX[f"Team_{self._safe_id(key)}"]
            self.crew_uris[key] = uri

            # Mapping table 3: Crew class instantiation → Team individual
            self.g.add((uri, RDF.type, AGENTO.Team))
            self.g.add((uri, DCTERMS.title, Literal(crew.crew_class_name, datatype=XSD.string)))

            # --- Agent Members ---
            # Mapping table 3: Crew.agents → hasAgentMember → LLMAgent
            for agent_key in crew.agent_keys:
                if agent_key in self.agent_uris:
                    self.g.add((uri, AGENTO.hasAgentMember, self.agent_uris[agent_key]))

            # --- Coordination Pattern ---
            # Mapping table 3: Crew.process → employsCoordinationPattern
            pattern_map = {
                "sequential": "Sequential",
                "hierarchical": "Hierarchical",
            }
            pattern_name = pattern_map.get(crew.process, "Custom")
            pattern_uri = AGENTO[pattern_name]
            self.g.add((pattern_uri, RDF.type, AGENTO.CoordinationPattern))
            self.g.add((uri, AGENTO.employsCoordinationPattern, pattern_uri))

            # --- Termination ---
            # Mapping table 3: Crew implicit termination → TaskCompletionTermination
            term_uri = EX[f"Termination_{self._safe_id(key)}"]
            self.g.add((term_uri, RDF.type, AGENTO.TaskCompletionTermination))
            self.g.add((uri, AGENTO.hasTerminationCondition, term_uri))

            # --- Workflow Pattern ---
            # Mapping table 3: Crew.tasks → WorkflowPattern with WorkflowSteps
            wp_uri = EX[f"WorkflowPattern_{self._safe_id(key)}"]
            self.g.add((wp_uri, RDF.type, AGENTO.WorkflowPattern))
            self.g.add((uri, AGENTO.hasWorkflowPattern, wp_uri))

            prev_step_uri = None
            for idx, task_key in enumerate(crew.task_keys):
                step_uri = EX[f"CrewStep_{self._safe_id(key)}_{self._safe_id(task_key)}"]

                # Determine step type based on position
                is_first = idx == 0
                is_last = idx == len(crew.task_keys) - 1

                if is_first and is_last:
                    # Single-step crew: both StartStep and EndStep
                    self.g.add((step_uri, RDF.type, AGENTO.StartStep))
                    self.g.add((step_uri, RDF.type, AGENTO.EndStep))
                elif is_first:
                    self.g.add((step_uri, RDF.type, AGENTO.StartStep))
                elif is_last:
                    self.g.add((step_uri, RDF.type, AGENTO.EndStep))
                else:
                    self.g.add((step_uri, RDF.type, AGENTO.WorkflowStep))

                self.g.add((step_uri, DCTERMS.title, Literal(task_key, datatype=XSD.string)))
                self.g.add((step_uri, AGENTO.stepOrder, Literal(idx + 1, datatype=XSD.integer)))

                # Link step to task
                if task_key in self.task_uris:
                    self.g.add((step_uri, AGENTO.hasAssociatedTask, self.task_uris[task_key]))

                # Link sequential steps
                if prev_step_uri is not None:
                    self.g.add((prev_step_uri, AGENTO.nextStep, step_uri))

                self.g.add((wp_uri, AGENTO.hasWorkflowStep, step_uri))
                prev_step_uri = step_uri

            # --- System Config ---
            if crew.verbose:
                self._add_config(uri, AGENTO.hasSystemConfig, "verbose", "true")

            # --- Crew-level Memory ---
            # Mapping table 3: Crew.memory=True → hasTeamMemoryBinding
            if crew.memory:
                mb_uri = EX[f"MemoryBinding_Team_{self._safe_id(key)}"]
                mem_uri = EX[f"Memory_Team_{self._safe_id(key)}"]
                self.g.add((mb_uri, RDF.type, AGENTO.MemoryBinding))
                self.g.add((mb_uri, AGENTO.hasMemoryScope, Literal("GroupShared", datatype=XSD.string)))
                self.g.add((mb_uri, AGENTO.bindsMemory, mem_uri))
                self.g.add((mem_uri, RDF.type, AGENTO.Memory))
                self.g.add((mem_uri, AGENTO.hasPersistenceScope, Literal("Persistent", datatype=XSD.string)))
                self.g.add((uri, AGENTO.hasTeamMemoryBinding, mb_uri))

            log.info("  [Team] %s → %s (process: %s)", key, uri, crew.process)

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
        orch_uri = EX[f"Orchestration_{self._safe_id(flow.class_name)}"]
        self.g.add((orch_uri, RDF.type, AGENTO.Orchestration))
        self.g.add((orch_uri, DCTERMS.title, Literal(flow.class_name, datatype=XSD.string)))

        # Mapping table 4: Flow coordination pattern → Custom
        custom_uri = AGENTO.Custom
        self.g.add((custom_uri, RDF.type, AGENTO.CoordinationPattern))
        self.g.add((orch_uri, AGENTO.employsCoordinationPattern, custom_uri))

        # --- Link to crews ---
        # Mapping table 4: Crew references inside Flow → orchestratesTeam
        for crew_ref in flow.crew_references:
            if crew_ref in self.crew_uris:
                self.g.add((orch_uri, AGENTO.orchestratesTeam, self.crew_uris[crew_ref]))

        # --- Flow Workflow Pattern ---
        wp_uri = EX[f"FlowWorkflowPattern_{self._safe_id(flow.class_name)}"]
        self.g.add((wp_uri, RDF.type, AGENTO.WorkflowPattern))
        self.g.add((orch_uri, AGENTO.hasWorkflowPattern, wp_uri))

        # --- Build step URIs and resolve routing ---
        step_uris: dict[str, URIRef] = {}
        step_order = 1

        # Phase 1: Create all step individuals
        for step in flow.steps:
            step_uri = EX[f"FlowStep_{self._safe_id(step.method_name)}"]
            step_uris[step.method_name] = step_uri

            # Mapping table 4: Determine step type from decorator
            if step.decorator_type == "start":
                self.g.add((step_uri, RDF.type, AGENTO.StartStep))
            elif step.decorator_type == "router":
                self.g.add((step_uri, RDF.type, AGENTO.ConditionalStep))
            elif step.decorator_type == "listen":
                # Listen steps with no outgoing connections are EndSteps.
                # We determine this in Phase 2 after resolving all edges.
                self.g.add((step_uri, RDF.type, AGENTO.WorkflowStep))
            else:
                self.g.add((step_uri, RDF.type, AGENTO.WorkflowStep))

            self.g.add((step_uri, DCTERMS.title, Literal(step.method_name, datatype=XSD.string)))
            self.g.add((step_uri, AGENTO.stepOrder, Literal(step_order, datatype=XSD.integer)))
            self.g.add((wp_uri, AGENTO.hasWorkflowStep, step_uri))

            # Store routing logic for router steps
            if step.decorator_type == "router" and step.function_body:
                self.g.add((step_uri, AGENTO.hasRoutingLogic,
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
                        self.g.add((step_uris[step.method_name], AGENTO.nextStep,
                                    label_to_step[ret_val]))
                        outgoing_edges[step.method_name].append(ret_val)

            elif step.decorator_type == "start":
                # @start methods flow to the next step — which is the
                # method that has @router(this_method) or @listen(this_method)
                for other in flow.steps:
                    if other.decorator_type in ("router", "listen"):
                        for arg in other.decorator_args:
                            if arg == step.method_name:
                                self.g.add((step_uris[step.method_name], AGENTO.nextStep,
                                            step_uris[other.method_name]))
                                outgoing_edges[step.method_name].append(other.method_name)

        # Phase 3: Reclassify listen steps with no outgoing edges as EndStep
        for step in flow.steps:
            if step.decorator_type == "listen" and not outgoing_edges[step.method_name]:
                step_uri = step_uris[step.method_name]
                # Remove generic WorkflowStep type and add EndStep
                self.g.remove((step_uri, RDF.type, AGENTO.WorkflowStep))
                self.g.add((step_uri, RDF.type, AGENTO.EndStep))

        log.info("  [Flow] %s → %s (%d steps, %d crew references)",
                 flow.class_name, orch_uri, len(flow.steps), len(flow.crew_references))

    # -----------------------------------------------------------
    # System-Level Population
    # Mapping table Section 6
    # -----------------------------------------------------------

    def _populate_system(self) -> None:
        """Create the AgenticSystem individual that contains everything."""
        sys_uri = EX[self._safe_id(self.system_name)]

        # Mapping table 6: Entire source file → AgenticSystem
        self.g.add((sys_uri, RDF.type, AGENTO.AgenticSystem))

        # Mapping table 6: hasSourceFramework = "CrewAI"
        self.g.add((sys_uri, AGENTO.hasSourceFramework, Literal("CrewAI", datatype=XSD.string)))

        # Mapping table 6: All Crew instances → containsTeam
        for crew_uri in self.crew_uris.values():
            self.g.add((sys_uri, AGENTO.containsTeam, crew_uri))

        # Mapping table 6: All Agent instances → containsAgent
        for agent_uri in self.agent_uris.values():
            self.g.add((sys_uri, AGENTO.containsAgent, agent_uri))

        # Mapping table 6: Flow instance → containsOrchestration
        if self.parser.flow:
            orch_uri = EX[f"Orchestration_{self._safe_id(self.parser.flow.class_name)}"]
            self.g.add((sys_uri, AGENTO.containsOrchestration, orch_uri))

        log.info("  [System] %s → %s", self.system_name, sys_uri)

    # -----------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------

    def _add_config(
        self, subject: URIRef, property_uri: URIRef, key: str, value: str
    ) -> None:
        """Create a Config individual and link it to the subject."""
        config_uri = EX[f"Config_{self._safe_id(key)}_{self._safe_id(str(subject).split('#')[-1])}"]
        self.g.add((config_uri, RDF.type, AGENTO.Config))
        self.g.add((config_uri, AGENTO.configKey, Literal(key, datatype=XSD.string)))
        self.g.add((config_uri, AGENTO.configValue, Literal(value, datatype=XSD.string)))
        self.g.add((subject, property_uri, config_uri))

    @staticmethod
    def _safe_id(name: str) -> str:
        """Convert a name to a URI-safe identifier."""
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")


# ===================================================================
# MAIN PIPELINE
# ===================================================================

def main() -> None:
    """
    Execute the full extraction and population pipeline.

    This function orchestrates the three-layer architecture:
    1. Parse CrewAI source code into intermediate representations
    2. Populate the ontology from intermediate representations
    3. Serialize the populated ontology to Turtle format
    """
    # --- Layer 1 + 2: Parsing ---
    parser = CrewAISourceParser(SOURCE_DIR)
    parser.parse_all()

    # --- Layer 3: Ontology Population ---
    populator = OntologyPopulator(parser, system_name="EmailFlowSystem")
    graph = populator.populate()

    # --- Serialization ---
    output_path = Path(__file__).parent / "email_flow_ontology.ttl"
    graph.serialize(destination=str(output_path), format="turtle")
    log.info("")
    log.info("Ontology written to: %s", output_path)
    log.info("Total triples: %d", len(graph))

    # --- Validation Summary ---
    print("\n" + "=" * 60)
    print("EXTRACTION VALIDATION REPORT")
    print("=" * 60)
    _print_validation_report(graph, parser)


def _print_validation_report(graph: Graph, parser: CrewAISourceParser) -> None:
    """
    Print a summary of what was extracted and populated, highlighting
    any properties that could not be populated (information loss).
    """
    # Count individuals by type
    type_counts = {}
    for s, p, o in graph.triples((None, RDF.type, None)):
        type_name = str(o).split("#")[-1]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    print("\nIndividuals by class:")
    for cls, count in sorted(type_counts.items()):
        print(f"  {cls}: {count}")

    # Check for unpopulated properties (information loss)
    print("\nInformation loss analysis:")
    loss_items = []

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

    # Properties never exercised by this example
    print("\nProperties not exercised by this example (not information loss):")
    unexercised = [
        "hasMemoryBinding (no memory configured)",
        "employsReasoningPattern (reasoning not enabled)",
        "dependsOn (no task dependencies via context=)",
        "taskToolUsage (no task-level tools)",
        "hasGuardrail (no guardrail= on tasks)",
        "hasHumanCheckpoint (no human_input=True)",
        "interactsWith (single-agent crews)",
        "hasSubTeam (no nested teams at crew level)",
    ]
    for prop in unexercised:
        print(f"  {prop}")


if __name__ == "__main__":
    main()
