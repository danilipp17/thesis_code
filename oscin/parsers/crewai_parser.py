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

    def _extract_tool_decorated_functions(self, tree: ast.Module, filepath: Path) -> None:
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

            # --- Locate YAML config paths and class-level attributes ---
            agents_yaml_path = None
            tasks_yaml_path = None
            class_llm = None
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            val = self._extract_constant_value(item.value)
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
                    method, agents_yaml, str(filepath), class_llm=class_llm
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
        local_vars = self._collect_local_assignments(method)
        tools = self._extract_tool_references(agent_call, local_vars)
        llm = self._extract_keyword_string(agent_call, "llm")
        # If llm=self.llm (attribute access), resolve from class-level assignment
        if not llm:
            llm = self._resolve_llm_from_call(agent_call, class_llm)
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

        return ExtractedTeam(
            team_class_name=crew_class_name,
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
                    elif isinstance(elt, ast.Call) and isinstance(elt.func, ast.Attribute):
                        # e.g. GmailGetThread(api_resource=...) via chained call
                        tools.append(elt.func.value.id if isinstance(elt.func.value, ast.Name) else elt.func.attr)
                    elif isinstance(elt, ast.Name):
                        # Resolve local variable to class name if possible
                        resolved = local_vars.get(elt.id, elt.id)
                        tools.append(resolved)
                    elif isinstance(elt, ast.Attribute):
                        # e.g. CreateDraftTool.create_draft
                        tools.append(elt.attr)
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
    def _collect_local_assignments(method: ast.FunctionDef) -> dict[str, str]:
        """
        Collect local variable assignments of the form ``x = ClassName(...)``
        inside a method body. Returns {variable_name: class_name}.
        """
        assignments: dict[str, str] = {}
        for stmt in method.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call):
                    if isinstance(stmt.value.func, ast.Name):
                        assignments[target.id] = stmt.value.func.id
        return assignments

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
