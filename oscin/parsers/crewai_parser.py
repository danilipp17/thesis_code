"""
crewai_parser.py
================
CrewAI-specific source code parser.

Reads CrewAI projects that follow the ``@CrewBase`` / Flow pattern
and produces the shared intermediate representations.

Extraction order
----------------
1. Tools   — ``tools/*.py``  (BaseTool subclasses)
2. Pydantic models — all ``*.py`` (for Task.output_pydantic)
3. Crews   — ``crews/**/*.py`` (@CrewBase classes + YAML configs)
4. Flow    — ``main.py``  (Flow subclass with @start / @listen / @router)

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any, Optional
from oscin.parsers import ast_utils

import yaml

from oscin.base_parser import BaseSourceParser
from oscin.intermediate import (
    ExtractedAgent,
    ExtractedFlow,
    ExtractedFlowStep,
    ExtractedPydanticModel,
    ExtractedTask,
    ExtractedTeam,
    ExtractedTool,
)

log = logging.getLogger("oscin")


class CrewAIParser(BaseSourceParser):
    """
    Parses CrewAI source files and extracts intermediate representations.

    This class encapsulates all AST-level logic for the CrewAI framework.
    It does NOT know about the ontology — it only produces Extracted*
    objects.  The ontology population layer consumes these objects.
    """

    # -----------------------------------------------------------
    # Abstract interface
    # -----------------------------------------------------------

    @staticmethod
    def framework_name() -> str:
        return "CrewAI"

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

        self.log_extraction_summary()

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
            self._extract_tool_decorated_functions(tree, py_file)

    def _extract_basetool_subclasses(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect classes inheriting from BaseTool and extract:
        - name (class attribute)       → hasTitle
        - description (class attribute) → hasDescription
        - args_schema (Pydantic model) → hasInputSchema
        - _run method                  → hasImplementationReference
        """
        # First pass: collect Pydantic input schema models defined
        # in the same file (they are args_schema targets).
        local_schemas: dict[str, dict[str, str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if ast_utils.inherits_from(node, "BaseModel"):
                    fields = ast_utils.extract_pydantic_fields(node)
                    local_schemas[node.name] = fields

        # Second pass: find BaseTool subclasses.
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not ast_utils.inherits_from(node, "BaseTool"):
                continue

            tool_name = ""
            tool_desc = ""
            schema_class_name = ""

            for item in node.body:
                # BaseTool class attributes are ast.AnnAssign nodes
                # e.g. name: str = "Character Counter Tool"
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    attr_name = item.target.id
                    attr_value = ast_utils.extract_constant_value(item.value)

                    if attr_name == "name" and attr_value:
                        tool_name = attr_value
                    elif attr_name == "description" and attr_value:
                        tool_desc = attr_value
                    elif attr_name == "args_schema" and isinstance(
                        item.value, ast.Name
                    ):
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
                tool.name,
                filepath.name,
            )

    def _extract_tool_decorated_functions(
        self, tree: ast.Module, filepath: Path
    ) -> None:
        """
        Detect @tool-decorated functions (langchain / crewai pattern).

        Patterns handled:
        - Standalone: @tool("Tool Name") def func(...)
        - Inside a class: class Foo: @tool("Tool Name") def method(...)
        """
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                # Match @tool("name") or @tool
                func_node = deco.func if isinstance(deco.func, ast.Name) else None
                if func_node is None or func_node.id != "tool":
                    continue

                # Extract tool name from decorator argument
                tool_name = node.name
                if deco.args and isinstance(deco.args[0], ast.Constant):
                    tool_name = str(deco.args[0].value)

                # Extract description from the function docstring
                tool_desc = ast.get_docstring(node) or ""

                module_path = self._filepath_to_module(filepath)
                impl_ref = f"{module_path}.{node.name}"

                # Use a stable key that agents can reference
                tool_key = node.name
                tool = ExtractedTool(
                    class_name=tool_key,
                    name=tool_name,
                    description=tool_desc.strip(),
                    args_schema_json="{}",
                    implementation_ref=impl_ref,
                    source_file=str(filepath),
                )
                self.tools[tool_key] = tool
                log.info(
                    "  [Tool] Extracted @tool '%s' from %s",
                    tool.name,
                    filepath.name,
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
                if isinstance(node, ast.ClassDef) and ast_utils.inherits_from(
                    node, "BaseModel"
                ):
                    # Skip tool input schemas (already handled)
                    if node.name.endswith("Input"):
                        continue
                    fields = ast_utils.extract_pydantic_fields(node)
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
            if not ast_utils.has_decorator(node, "CrewBase"):
                continue

            crew_class_name = node.name
            log.info("  [Crew] Found @CrewBase class: %s", crew_class_name)

            # --- Locate YAML config paths and class-level attributes ---
            agents_yaml_path = None
            tasks_yaml_path = None
            class_llm = None
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            val = ast_utils.extract_constant_value(item.value)
                            if target.id == "agents_config" and val:
                                agents_yaml_path = filepath.parent / val
                            elif target.id == "tasks_config" and val:
                                tasks_yaml_path = filepath.parent / val
                            elif target.id == "llm":
                                class_llm = self._extract_llm_string(item.value)

            # --- Parse YAML configs ---
            agents_yaml = {}
            tasks_yaml = {}
            if agents_yaml_path and agents_yaml_path.exists():
                agents_yaml = yaml.safe_load(agents_yaml_path.read_text()) or {}
                log.info(
                    "    Loaded %d agent(s) from %s",
                    len(agents_yaml),
                    agents_yaml_path.name,
                )
            if tasks_yaml_path and tasks_yaml_path.exists():
                tasks_yaml = yaml.safe_load(tasks_yaml_path.read_text()) or {}
                log.info(
                    "    Loaded %d task(s) from %s",
                    len(tasks_yaml),
                    tasks_yaml_path.name,
                )

            # --- Extract agents from @agent methods ---
            agent_keys_in_crew = []
            for method in ast_utils.iter_methods(node):
                if not ast_utils.has_decorator(method, "agent"):
                    continue
                agent_key = method.name  # Method name = agent key
                agent_info = self._extract_agent_from_method(
                    method, agents_yaml, str(filepath), class_llm=class_llm
                )
                if agent_info:
                    self.agents[agent_key] = agent_info
                    agent_keys_in_crew.append(agent_key)
                    log.info("    [Agent] '%s' (role: %s)", agent_key, agent_info.role)

            # --- Extract tasks from @task methods ---
            task_keys_in_crew = []
            for method in ast_utils.iter_methods(node):
                if not ast_utils.has_decorator(method, "task"):
                    continue
                task_key = method.name  # Method name = task key
                task_info = self._extract_task_from_method(
                    method, tasks_yaml, str(filepath)
                )
                if task_info:
                    self.tasks[task_key] = task_info
                    task_keys_in_crew.append(task_key)
                    log.info(
                        "    [Task] '%s' (agent: %s)", task_key, task_info.agent_key
                    )

            # --- Extract Crew() configuration from @crew method ---
            crew_info = self._extract_crew_config(
                node,
                crew_class_name,
                agent_keys_in_crew,
                task_keys_in_crew,
                str(filepath),
            )
            self.teams[crew_class_name] = crew_info

    def _extract_agent_from_method(
        self,
        method: ast.FunctionDef,
        agents_yaml: dict,
        source_file: str,
        class_llm: Optional[str] = None,
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
        agent_call = ast_utils.find_call_in_method(method, "Agent")
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
        local_vars = ast_utils.collect_local_assignments(method)
        tools = self._extract_tool_references(agent_call, local_vars)
        llm = ast_utils.extract_keyword_string(agent_call, "llm")
        # If llm=self.llm (attribute access), resolve from class-level assignment
        if not llm:
            llm = self._resolve_llm_from_call(agent_call, class_llm)
        verbose = ast_utils.extract_keyword_bool(agent_call, "verbose")
        allow_delegation = ast_utils.extract_keyword_bool(agent_call, "allow_delegation")
        reasoning = ast_utils.extract_keyword_bool(agent_call, "reasoning") or False
        max_reasoning = ast_utils.extract_keyword_int(agent_call, "max_reasoning_attempts")
        memory = ast_utils.extract_keyword_bool(agent_call, "memory") or False
        knowledge_sources = self._extract_knowledge_sources(agent_call, local_vars)

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
            knowledge_sources=knowledge_sources,
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
        task_call = ast_utils.find_call_in_method(method, "Task")
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
        output_pydantic = ast_utils.extract_keyword_name(task_call, "output_pydantic")
        output_json = ast_utils.extract_keyword_name(task_call, "output_json")
        tools = self._extract_tool_references(task_call)
        human_input = ast_utils.extract_keyword_bool(task_call, "human_input") or False

        # Context (task dependencies): context=[task_a, task_b]
        # In CrewAI, context is often passed as context=[self.data_gathering()]
        context_tasks = []
        context_kw = ast_utils.find_keyword(task_call, "context")
        if context_kw and isinstance(context_kw.value, ast.List):
            for elt in context_kw.value.elts:
                if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Attribute):
                    context_tasks.append(elt.func.attr)
                elif isinstance(elt, ast.Name):
                    context_tasks.append(elt.id)

        # C1: Detect guardrail type (FunctionBased vs LLMBased) and extract details
        guardrails = []
        guardrail_kw = ast_utils.find_keyword(task_call, "guardrail")
        if guardrail_kw:
            guardrails = self._extract_guardrails(guardrail_kw, method)
        # Also check plural 'guardrails' kwarg
        guardrails_kw = ast_utils.find_keyword(task_call, "guardrails")
        if guardrails_kw:
            guardrails.extend(self._extract_guardrails(guardrails_kw, method))

        # C2: Extract guardrail_max_retries
        guardrail_max_retries = ast_utils.extract_keyword_int(
            task_call, "guardrail_max_retries"
        )

        # Delegation strategy based on agent assignment
        delegation = "ExplicitAssignment" if agent_key else ""

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
            guardrails=guardrails,
            delegation_strategy=delegation,
            source_file=source_file,
        )

    def _extract_crew_config(
        self,
        class_node: ast.ClassDef,
        crew_class_name: str,
        agent_keys: list[str],
        task_keys: list[str],
        source_file: str,
    ) -> ExtractedTeam:
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
        knowledge_sources = []

        for method in ast_utils.iter_methods(class_node):
            if not ast_utils.has_decorator(method, "crew"):
                continue

            crew_call = ast_utils.find_call_in_method(method, "Crew")
            if not crew_call:
                continue

            # Extract process type
            # Pattern: process=Process.sequential or process=Process.hierarchical
            process_kw = ast_utils.find_keyword(crew_call, "process")
            if process_kw and isinstance(process_kw.value, ast.Attribute):
                process = process_kw.value.attr  # "sequential" or "hierarchical"

            verbose = ast_utils.extract_keyword_bool(crew_call, "verbose") or False
            memory = ast_utils.extract_keyword_bool(crew_call, "memory") or False
            manager_llm = ast_utils.extract_keyword_string(crew_call, "manager_llm")
            manager_agent = ast_utils.extract_keyword_name(crew_call, "manager_agent")

            # Use local_vars = {} here since crew definition typically doesn't use complex locals for knowledge
            knowledge_sources = self._extract_knowledge_sources(crew_call, {})

        return ExtractedTeam(
            team_class_name=crew_class_name,
            agent_keys=agent_keys,
            task_keys=task_keys,
            process=process,
            verbose=verbose,
            memory=memory,
            manager_llm=manager_llm,
            manager_agent=manager_agent,
            knowledge_sources=knowledge_sources,
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
            if not ast_utils.inherits_from(node, "Flow"):
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

            for method in ast_utils.iter_methods(node):
                step = self._extract_flow_step(method, source)
                if step:
                    steps.append(step)
                    if step.calls_crew:
                        crew_references.add(step.calls_crew)
                    log.info(
                        "    [FlowStep] %s: %s%s",
                        step.step_type,
                        step.method_name,
                        f" → calls {step.calls_crew}" if step.calls_crew else "",
                    )

            # Copy Pydantic state-model fields onto the Flow so the
            # populator can persist them as :hasSchemaDefinition. Without
            # this the state_fields dict stays empty and the reader has to
            # synthesize fake fields from task outputs.
            state_fields: dict[str, str] = {}
            if state_model and state_model in self.pydantic_models:
                for fname, finfo in self.pydantic_models[state_model].fields.items():
                    if isinstance(finfo, dict):
                        state_fields[fname] = finfo.get("type") or "Any"
                    else:
                        state_fields[fname] = str(finfo)

            self.flow = ExtractedFlow(
                class_name=flow_class_name,
                state_model=state_model,
                steps=steps,
                crew_references=list(crew_references),
                source_file=str(main_py),
                state_fields=state_fields,
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
        step_type = None
        dependencies: list[str] = []

        for deco in method.decorator_list:
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name):
                deco_name = deco.func.id
                if deco_name in ("start", "listen", "router"):
                    step_type = deco_name
                    # Extract arguments (string labels or method references)
                    for arg in deco.args:
                        if isinstance(arg, ast.Constant):
                            dependencies.append(str(arg.value))
                        elif isinstance(arg, ast.Name):
                            dependencies.append(arg.id)
            elif isinstance(deco, ast.Name):
                # Bare decorator without parentheses: @start
                if deco.id in ("start", "listen", "router"):
                    step_type = deco.id

        if not step_type:
            return None

        # Map to common IR step types
        if step_type == "listen":
            step_type = "regular"
        elif step_type == "router":
            step_type = "conditional"

        # Detect crew.kickoff() calls in the method body.
        # Pattern: SomeCrewClass().crew().kickoff(...)
        calls_crew = self._find_crew_kickoff_in_method(method)

        # For @router methods, extract return values
        return_values = []
        if step_type == "conditional":
            return_values = ast_utils.extract_return_values(method)

        # Serialize the function body for routing logic storage.
        # We capture the entire method body (all statements) so that
        # the routing logic is complete and can be interpreted by a
        # generator targeting a different framework.
        function_body = ""
        if step_type == "conditional":
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
                function_body = "\n".join(ast.unparse(stmt) for stmt in method.body)

        return ExtractedFlowStep(
            method_name=method.name,
            step_type=step_type,
            dependencies=dependencies,
            calls_crew=calls_crew,
            return_values=return_values,
            function_body=function_body,
        )

    # -----------------------------------------------------------
    # AST Helper Methods
    # -----------------------------------------------------------












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

    def _extract_knowledge_sources(
        self, call: ast.Call, local_vars: Optional[dict[str, str]] = None
    ) -> list[str]:
        """
        Extract knowledge sources from knowledge=[source1, source2].
        Handles instantiations, local variable references, and strings.
        """
        local_vars = local_vars or {}
        sources = []
        for kw in call.keywords:
            if kw.arg == "knowledge" and isinstance(kw.value, ast.List):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name):
                        sources.append(elt.func.id)
                    elif isinstance(elt, ast.Name):
                        resolved = local_vars.get(elt.id, elt.id)
                        sources.append(resolved)
                    elif isinstance(elt, ast.Attribute):
                        sources.append(elt.attr)
                    elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        sources.append(elt.value)
        return sources

    def _extract_tool_references(
        self, call: ast.Call, local_vars: Optional[dict[str, str]] = None
    ) -> list[str]:
        """
        Extract tool class/function names from tools=[ToolA(), ToolB()].

        Handles:
        - ToolClass()           → "ToolClass"
        - tool_variable         → resolved via local_vars or kept as-is
        - Cls.method            → "method" (e.g. CreateDraftTool.create_draft)
        - ToolClass(kw=val)     → "ToolClass"
        """
        local_vars = local_vars or {}
        tools = []
        for kw in call.keywords:
            if kw.arg == "tools" and isinstance(kw.value, ast.List):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name):
                        tools.append(elt.func.id)
                    elif isinstance(elt, ast.Call) and isinstance(
                        elt.func, ast.Attribute
                    ):
                        # e.g. GmailGetThread(api_resource=...) via chained call
                        tools.append(
                            elt.func.value.id
                            if isinstance(elt.func.value, ast.Name)
                            else elt.func.attr
                        )
                    elif isinstance(elt, ast.Name):
                        # Resolve local variable to class name if possible
                        resolved = local_vars.get(elt.id, elt.id)
                        tools.append(resolved)
                    elif isinstance(elt, ast.Attribute):
                        # e.g. CreateDraftTool.create_draft
                        tools.append(elt.attr)
        return tools

    def _extract_guardrails(
        self, kw: ast.keyword, method: ast.FunctionDef
    ) -> list[str]:
        """
        C1: Extract guardrail info with type detection.

        Returns list of strings encoding guardrail type and details:
        - "FunctionBased:<function_body>" for callable guardrails
        - "LLMBased:<description>" for string-based guardrails
        """
        guardrails = []
        elements = []
        if isinstance(kw.value, ast.List):
            elements = kw.value.elts
        else:
            elements = [kw.value]

        for elt in elements:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                # String literal → LLMBased
                guardrails.append(f"LLMBased:{elt.value}")
            elif isinstance(elt, ast.Name):
                # Function reference → FunctionBased
                # Try to find the function body in the method's scope or module
                guardrails.append(f"FunctionBased:{elt.id}")
            elif isinstance(elt, ast.Call):
                # Function call → FunctionBased
                call_name = ""
                if isinstance(elt.func, ast.Name):
                    call_name = elt.func.id
                elif isinstance(elt.func, ast.Attribute):
                    call_name = elt.func.attr
                guardrails.append(f"FunctionBased:{call_name}")
            else:
                guardrails.append("FunctionBased:unknown")
        return guardrails


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
                    if isinstance(inner, ast.Call) and isinstance(
                        inner.func, ast.Attribute
                    ):
                        if inner.func.attr == "crew":
                            # Now find the class instantiation
                            obj = inner.func.value
                            if isinstance(obj, ast.Call) and isinstance(
                                obj.func, ast.Name
                            ):
                                return obj.func.id
        return None


    @staticmethod
    def _pydantic_fields_to_json_schema(fields: dict[str, dict[str, str] | str]) -> str:
        """
        Convert extracted Pydantic field definitions to a JSON Schema string.
        Delegates to :func:`oscin.utils.pydantic_fields_to_json_schema`.
        """
        from oscin.utils import pydantic_fields_to_json_schema

        return pydantic_fields_to_json_schema(fields)

    @staticmethod
    def _clean_yaml_string(value: Any) -> str:
        """Strip trailing whitespace and newlines from YAML block scalars."""
        if value is None:
            return ""
        return str(value).strip()


    @staticmethod
    def _extract_llm_string(node: ast.expr) -> Optional[str]:
        """
        Extract a human-readable LLM identifier from an AST expression.

        Handles patterns like:
        - ChatOpenAI(model="gpt-4o")  → "gpt-4o"
        - LLM(model="claude-3")       → "claude-3"
        - "gpt-4o"                     → "gpt-4o"
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Call):
            # Look for model= keyword
            for kw in node.keywords:
                if kw.arg == "model" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
            # Fallback: use the class name
            if isinstance(node.func, ast.Name):
                return node.func.id
            if isinstance(node.func, ast.Attribute):
                return node.func.attr
        return None

    @staticmethod
    def _resolve_llm_from_call(
        call: ast.Call, class_llm: Optional[str]
    ) -> Optional[str]:
        """
        If the call has llm=self.llm or llm=self.<attr>, return
        the class-level LLM value.
        """
        for kw in call.keywords:
            if kw.arg == "llm" and isinstance(kw.value, ast.Attribute):
                if isinstance(kw.value.value, ast.Name) and kw.value.value.id == "self":
                    return class_llm
        return None

    @staticmethod
    def _filepath_to_module(filepath: Path) -> str:
        """Convert a file path to a dotted Python module path."""
        parts = filepath.with_suffix("").parts
        # Find the package root (heuristic: start from "tools" or "crews")
        for i, part in enumerate(parts):
            if part in ("tools", "crews", "src"):
                return ".".join(parts[i:])
        return ".".join(parts[-3:])
