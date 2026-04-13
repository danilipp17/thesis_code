"""
autogen_parser.py
=================
AutoGen v0.4 specific source code parser.

Reads AutoGen v0.4 projects and produces the shared intermediate
representations defined in :mod:`oscin.intermediate`.

AutoGen v0.4 Construct → Intermediate Mapping
-----------------------------------------
- ``AssistantAgent(name=..., system_message=..., model_client=..., tools=[...])``
      → ``ExtractedAgent(role=name, backstory=system_message)``
- ``OpenAIChatCompletionClient(model="...")``
      → Extracts LLM resolution for agents
- ``FunctionTool(func, description="...")``
      → ``ExtractedTool(...)`` with explicit description
- ``RoundRobinGroupChat(participants=[...], max_turns=N)``
      → ``ExtractedTeam(agent_keys=[...], max_turns=N)``
- ``team.run_stream(...)`` / ``team.run(...)``
      → ``ExtractedFlow`` / ``ExtractedFlowStep``

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
from typing import Optional

from oscin.base_parser import BaseSourceParser
from oscin.intermediate import (
    ExtractedAgent,
    ExtractedFlow,
    ExtractedFlowStep,
    ExtractedTask,
    ExtractedTeam,
    ExtractedTool,
)

log = logging.getLogger("oscin")

_AGENT_CLASSES = {"AssistantAgent", "UserProxyAgent"}

# Models known to have native reasoning capabilities
_REASONING_MODELS = {"o1", "o1-mini", "o1-preview", "o3", "o3-mini", "o3-pro"}

# Known AutoGen memory classes and their persistence scope
_MEMORY_PERSISTENCE = {
    "ListMemory": "ExecutionScoped",
    "ChromaDBVectorMemory": "Persistent",
    "RedisMemory": "Persistent",
}


class AutoGenParser(BaseSourceParser):
    @staticmethod
    def framework_name() -> str:
        return "AutoGen_v0.4"

    def parse_all(self) -> None:
        log.info("=" * 60)
        log.info("STARTING AUTOGEN SOURCE CODE EXTRACTION")
        log.info("Source directory: %s", self.source_dir)
        log.info("=" * 60)

        trees: list[tuple[Path, ast.Module]] = []
        for py_file in self.source_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(py_file))
                trees.append((py_file, tree))
            except SyntaxError:
                log.warning(f"SyntaxError parsing Python file: {py_file.name}")

        import nbformat

        for nb_file in self.source_dir.rglob("*.ipynb"):
            if ".ipynb_checkpoints" in str(nb_file):
                continue
            try:
                with open(nb_file, "r", encoding="utf-8") as f:
                    nb = nbformat.read(f, as_version=4)
                code_cells = [
                    cell["source"] for cell in nb.cells if cell.cell_type == "code"
                ]
                source = "\n\n".join(code_cells)
                tree = ast.parse(source, filename=str(nb_file))
                trees.append((nb_file, tree))
            except Exception as e:
                log.warning(f"Failed to parse notebook {nb_file.name}: {e}")

        # State to trace LLM definitions
        # variable_name -> model name (e.g. "gpt-4o")
        self.llm_clients: dict[str, str] = {}

        # variable_name -> agent_key (for resolving team participants)
        self._var_to_agent_key: dict[str, str] = {}

        # FunctionTool wrapping: variable_name -> (func_name, description)
        self._function_tools: dict[str, tuple[str, str]] = {}

        for filepath, tree in trees:
            self._extract_llms(tree, filepath)

        for filepath, tree in trees:
            self._extract_function_tools(tree, filepath)

        for filepath, tree in trees:
            self._extract_tools(tree, filepath)

        for filepath, tree in trees:
            self._extract_agents(tree, filepath)

        for filepath, tree in trees:
            self._extract_teams(tree, filepath)

        for filepath, tree in trees:
            self._extract_flow(tree, filepath)

        self.log_extraction_summary()

    # -----------------------------------------------------------
    # LLM Client Detection
    # -----------------------------------------------------------

    def _extract_llms(self, tree: ast.Module, filepath: Path) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    call_name = self._get_call_name(node.value)
                    if call_name == "OpenAIChatCompletionClient":
                        model = self._extract_keyword_string(node.value, "model")
                        if model:
                            self.llm_clients[target.id] = model
                            log.info(
                                "  [LLM] %s = OpenAIChatCompletionClient(model='%s') in %s",
                                target.id,
                                model,
                                filepath.name,
                            )

    # -----------------------------------------------------------
    # FunctionTool Detection
    # -----------------------------------------------------------

    def _extract_function_tools(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect ``FunctionTool(func, description="...")`` wrapping patterns.

        Builds a mapping from variable name to (function_name, description)
        so that agent tool references can be resolved.
        """
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Call):
                continue
            call_name = self._get_call_name(node.value)
            if call_name != "FunctionTool":
                continue

            # Extract the function reference (first positional arg)
            func_name = None
            if node.value.args and isinstance(node.value.args[0], ast.Name):
                func_name = node.value.args[0].id

            # Extract description keyword
            description = self._extract_keyword_string(node.value, "description") or ""

            if func_name:
                self._function_tools[target.id] = (func_name, description)
                log.info(
                    "  [FunctionTool] %s = FunctionTool(%s, desc='%s') in %s",
                    target.id,
                    func_name,
                    description[:60],
                    filepath.name,
                )

    # -----------------------------------------------------------
    # Tool Extraction
    # -----------------------------------------------------------

    def _extract_tools(self, tree: ast.Module, filepath: Path) -> None:
        """Extract tool functions. Enhances with FunctionTool descriptions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if node.name == "main":
                    continue
                # Check if this function is wrapped in a FunctionTool
                ft_description = ""
                for _var, (fn, desc) in self._function_tools.items():
                    if fn == node.name:
                        ft_description = desc
                        break

                # Extract argument schema from function signature
                args_schema = self._extract_tool_args_schema(node)

                tool = ExtractedTool(
                    class_name=node.name,
                    name=node.name,
                    description=ft_description or ast.get_docstring(node) or "",
                    args_schema_json=json.dumps(args_schema) if args_schema else "{}",
                    implementation_ref=f"{filepath.stem}.{node.name}",
                    source_file=str(filepath),
                )
                self.tools[node.name] = tool
                log.info(
                    "  [Tool] '%s' (desc from %s) from %s",
                    node.name,
                    "FunctionTool" if ft_description else "docstring",
                    filepath.name,
                )

    # -----------------------------------------------------------
    # Agent Extraction
    # -----------------------------------------------------------

    def _extract_agents(self, tree: ast.Module, filepath: Path) -> None:
        """Extract AssistantAgent and UserProxyAgent instantiations with variable-to-key mapping."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Call):
                continue

            class_name = self._get_call_name(node.value)
            if class_name not in _AGENT_CLASSES:
                continue

            # Name can be passed as keyword (name="x") or first positional arg ("x")
            name = self._extract_keyword_string(node.value, "name")
            if not name and node.value.args:
                first_arg = node.value.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    name = first_arg.value
            if not name:
                name = target.id  # Fall back to variable name
            system_message = (
                self._extract_keyword_string(node.value, "system_message") or ""
            )

            # A1: Extract description (orchestrator-facing prompt)
            description = (
                self._extract_keyword_string(node.value, "description") or ""
            )

            # Check for human input mode
            human_input_mode = self._extract_keyword_string(
                node.value, "human_input_mode"
            )
            has_human_checkpoint = False
            if human_input_mode in ("ALWAYS", "TERMINATE"):
                has_human_checkpoint = True
            # A3: UserProxyAgent is always a human checkpoint
            if class_name == "UserProxyAgent":
                has_human_checkpoint = True

            llm = None
            for kw in node.value.keywords:
                if kw.arg == "model_client" and isinstance(kw.value, ast.Name):
                    llm = self.llm_clients.get(kw.value.id)
                elif kw.arg == "llm_config" and isinstance(kw.value, ast.Dict):
                    # Autogen < 0.4 uses llm_config={"config_list": [{"model": "..."}]}
                    for key, val in zip(kw.value.keys, kw.value.values):
                        if (
                            isinstance(key, ast.Constant)
                            and key.value == "config_list"
                            and isinstance(val, ast.List)
                        ):
                            if val.elts and isinstance(val.elts[0], ast.Dict):
                                dict_node = val.elts[0]
                                for k, v in zip(dict_node.keys, dict_node.values):
                                    if (
                                        isinstance(k, ast.Constant)
                                        and k.value == "model"
                                        and isinstance(v, ast.Constant)
                                    ):
                                        llm = v.value

            # Resolve tool references
            tools = []
            for kw in node.value.keywords:
                if kw.arg == "tools" and isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Name):
                            # Resolve through FunctionTool mapping
                            if elt.id in self._function_tools:
                                func_name = self._function_tools[elt.id][0]
                                tools.append(func_name)
                            else:
                                tools.append(elt.id)

            # A7: Detect memory instances on agents
            has_memory = False
            memory_type = ""
            memory_persistence = ""
            for kw in node.value.keywords:
                if kw.arg == "memory" and isinstance(kw.value, ast.List):
                    has_memory = True
                    # Try to detect memory class types from list elements
                    for elt in kw.value.elts:
                        mem_class = None
                        if isinstance(elt, ast.Call):
                            mem_class = self._get_call_name(elt)
                        elif isinstance(elt, ast.Name):
                            mem_class = elt.id
                        if mem_class and mem_class in _MEMORY_PERSISTENCE:
                            memory_type = mem_class
                            memory_persistence = _MEMORY_PERSISTENCE[mem_class]

            # Heuristic: split system_message into goal and backstory
            goal, backstory = self._split_system_message(system_message)

            # A8: Detect reasoning from model name
            reasoning = False
            reasoning_origin = ""
            if llm and any(llm.startswith(m) for m in _REASONING_MODELS):
                reasoning = True
                reasoning_origin = "ModelNative"

            # A3: Set agent type
            agent_type = "UserProxy" if class_name == "UserProxyAgent" else "GeneralPurpose"

            agent_key = self._safe_key(name)

            # A2: AutoGen uses ModelDirective for system_message, or separate
            # ModelDirective + OrchestratorDirective when description is also present
            directive = "ModelDirective" if system_message else "DualDirective"

            agent = ExtractedAgent(
                agent_key=agent_key,
                role=name,
                goal=goal,
                backstory=backstory,
                llm=llm if class_name != "UserProxyAgent" else None,
                tools=tools,
                reasoning=reasoning,
                memory=has_memory,
                verbose=None,
                source_file=str(filepath),
                agent_type=agent_type,
                description=description,
                directive_function=directive,
                reasoning_origin=reasoning_origin,
                memory_type=memory_type,
                memory_persistence=memory_persistence,
                human_input=has_human_checkpoint,
            )
            self.agents[agent_key] = agent

            # Store variable-to-key mapping for team participant resolution
            self._var_to_agent_key[target.id] = agent_key
            log.info(
                "  [Agent] '%s' (var=%s, type=%s, llm=%s, tools=%s, desc=%s) from %s",
                name,
                target.id,
                agent_type,
                llm or "unknown",
                tools or "none",
                "yes" if description else "no",
                filepath.name,
            )

    # -----------------------------------------------------------
    # Team Extraction
    # -----------------------------------------------------------

    def _extract_teams(self, tree: ast.Module, filepath: Path) -> None:
        # A5: Pre-pass to collect termination condition variable assignments
        # e.g. text_term = TextMentionTermination("APPROVE")
        term_vars: dict[str, dict] = {}
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Call):
                continue
            call_name = self._get_call_name(node.value)
            if call_name == "TextMentionTermination":
                trigger = ""
                if node.value.args and isinstance(node.value.args[0], ast.Constant):
                    trigger = str(node.value.args[0].value)
                term_vars[target.id] = {"type": "EventBased", "trigger": trigger}
            elif call_name == "MaxMessageTermination":
                max_msgs = None
                if node.value.args and isinstance(node.value.args[0], ast.Constant):
                    max_msgs = node.value.args[0].value
                for kw in node.value.keywords:
                    if kw.arg == "max_messages" and isinstance(kw.value, ast.Constant):
                        max_msgs = kw.value.value
                term_vars[target.id] = {"type": "TurnLimit", "max_turns": max_msgs}
            elif call_name in ("TextMessageTermination", "HandoffTermination", "ExternalTermination"):
                term_vars[target.id] = {"type": "EventBased", "trigger": call_name}

        # A5: Detect composite termination (var_a | var_b or var_a & var_b)
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if isinstance(node.value, ast.BinOp):
                composite = self._extract_composite_termination(node.value, term_vars)
                if composite:
                    term_vars[target.id] = composite

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            class_name = self._get_call_name(node)
            if class_name not in [
                "RoundRobinGroupChat",
                "SelectorGroupChat",
                "Swarm",
                "MagenticOneGroupChat",
                "GroupChat",
            ]:
                continue

            agent_keys = []
            # 'participants' is used in v0.4, 'agents' is used in older autogen
            for param_name in ["participants", "agents"]:
                for kw in node.keywords:
                    if kw.arg == param_name and isinstance(kw.value, ast.List):
                        for elt in kw.value.elts:
                            if isinstance(elt, ast.Name):
                                # Resolve through variable-to-agent mapping
                                if elt.id in self._var_to_agent_key:
                                    agent_keys.append(self._var_to_agent_key[elt.id])
                                else:
                                    # Fallback: use the variable name as-is
                                    agent_keys.append(self._safe_key(elt.id))

            # Extract max_turns (v0.4) or max_round (older)
            max_turns = None
            for param_name in ["max_turns", "max_round"]:
                for kw in node.keywords:
                    if kw.arg == param_name and isinstance(kw.value, ast.Constant):
                        if isinstance(kw.value.value, int):
                            max_turns = kw.value.value

            # A5: Extract termination_condition kwarg
            termination_conditions = []
            for kw in node.keywords:
                if kw.arg == "termination_condition":
                    if isinstance(kw.value, ast.Name) and kw.value.id in term_vars:
                        tc = term_vars[kw.value.id]
                        if tc["type"] == "Composite":
                            termination_conditions = tc.get("conditions", [])
                            # Also store the composite itself
                            termination_conditions.append(tc)
                        else:
                            termination_conditions.append(tc)
                    elif isinstance(kw.value, ast.Call):
                        tc = self._parse_termination_call(kw.value)
                        if tc:
                            termination_conditions.append(tc)

            # A6: Map class to coordination pattern
            pattern_map = {
                "RoundRobinGroupChat": "RoundRobin",
                "SelectorGroupChat": "SelectorBased",
                "Swarm": "Swarm",
                "MagenticOneGroupChat": "Custom",
                "GroupChat": "RoundRobin",
            }
            coordination_pattern = pattern_map.get(class_name, "Custom")

            team = ExtractedTeam(
                team_class_name=class_name,
                agent_keys=agent_keys,
                task_keys=[],
                process="sequential",
                verbose=False,
                memory=False,
                manager_llm=None,
                max_turns=max_turns,
                coordination_pattern=coordination_pattern,
                termination_conditions=termination_conditions,
                source_file=str(filepath),
            )
            team_key = f"{class_name}_{len(self.teams)}"
            self.teams[team_key] = team
            log.info(
                "  [Team] %s with %d agents (pattern=%s, max_turns=%s, terminations=%d) from %s",
                class_name,
                len(agent_keys),
                coordination_pattern,
                max_turns,
                len(termination_conditions),
                filepath.name,
            )

    @staticmethod
    def _parse_termination_call(call: ast.Call) -> dict | None:
        """Parse a termination condition constructor call into a dict."""
        call_name = ""
        if isinstance(call.func, ast.Name):
            call_name = call.func.id
        elif isinstance(call.func, ast.Attribute):
            call_name = call.func.attr

        if call_name == "TextMentionTermination":
            trigger = ""
            if call.args and isinstance(call.args[0], ast.Constant):
                trigger = str(call.args[0].value)
            return {"type": "EventBased", "trigger": trigger}
        elif call_name == "MaxMessageTermination":
            max_msgs = None
            if call.args and isinstance(call.args[0], ast.Constant):
                max_msgs = call.args[0].value
            for kw in call.keywords:
                if kw.arg == "max_messages" and isinstance(kw.value, ast.Constant):
                    max_msgs = kw.value.value
            return {"type": "TurnLimit", "max_turns": max_msgs}
        elif call_name in ("TextMessageTermination", "HandoffTermination", "ExternalTermination"):
            return {"type": "EventBased", "trigger": call_name}
        return None

    @classmethod
    def _extract_composite_termination(cls, bin_op: ast.BinOp, term_vars: dict) -> dict | None:
        """Extract composite termination from binary operations (| or &)."""
        if isinstance(bin_op.op, ast.BitOr):
            operator = "OR"
        elif isinstance(bin_op.op, ast.BitAnd):
            operator = "AND"
        else:
            return None

        conditions = []
        for operand in (bin_op.left, bin_op.right):
            if isinstance(operand, ast.Name) and operand.id in term_vars:
                conditions.append(term_vars[operand.id])
            elif isinstance(operand, ast.BinOp):
                nested = cls._extract_composite_termination(operand, term_vars)
                if nested:
                    conditions.append(nested)

        if conditions:
            return {"type": "Composite", "operator": operator, "conditions": conditions}
        return None

    # -----------------------------------------------------------
    # Flow Extraction
    # -----------------------------------------------------------

    def _extract_flow(self, tree: ast.Module, filepath: Path) -> None:
        steps = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("run", "run_stream", "initiate_chat"):
                    caller = self._get_attr_value_name(node.func)

                    # A4: Extract task string from team.run(task="...")
                    task_string = self._extract_keyword_string(node, "task") or ""
                    # Also check first positional arg for initiate_chat
                    if not task_string and node.func.attr == "initiate_chat":
                        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            task_string = node.args[0].value

                    # For initiate_chat, try to extract who it interacts with
                    target = None
                    if node.args and isinstance(node.args[0], ast.Name):
                        target = node.args[0].id

                    method_title = f"run_{caller or 'unknown'}"
                    if node.func.attr == "initiate_chat":
                        method_title = f"initiate_chat_{caller or 'unknown'}_to_{target or 'unknown'}"

                    step = ExtractedFlowStep(
                        method_name=method_title,
                        decorator_type="start",
                        decorator_args=[],
                        calls_crew=target if target else caller,
                    )
                    steps.append(step)

                    # A4: Create a Task from the task string
                    if task_string:
                        task_key = f"autogen_task_{len(self.tasks)}"
                        task = ExtractedTask(
                            task_key=task_key,
                            description=task_string,
                            expected_output="",
                            agent_key=None,
                            delegation_strategy="OrchestratorDelegated",
                            source_file=str(filepath),
                        )
                        self.tasks[task_key] = task
                        log.info(
                            "  [Task] Extracted from %s(task=...) — '%s...' from %s",
                            node.func.attr,
                            task_string[:60],
                            filepath.name,
                        )

                    log.info(
                        "  [Flow] %s: %s from %s", node.func.attr, caller, filepath.name
                    )

        if steps and not self.flow:
            self.flow = ExtractedFlow(
                class_name="AutoGenFlow",
                state_model=None,
                steps=steps,
                crew_references=[],
                source_file=str(filepath),
            )

    # -----------------------------------------------------------
    # Helper: Split system_message into goal + backstory
    # -----------------------------------------------------------

    @staticmethod
    def _split_system_message(system_message: str) -> tuple[str, str]:
        """
        Heuristic split of AutoGen system_message into goal and backstory.

        The first sentence (typically "You are a...") becomes the goal.
        The remainder becomes the backstory.
        """
        if not system_message:
            return "", ""

        # Split on first period that's followed by a space
        parts = system_message.split(". ", 1)
        if len(parts) == 2:
            goal = parts[0].strip() + "."
            backstory = parts[1].strip()
            return goal, backstory

        return system_message.strip(), ""

    # -----------------------------------------------------------
    # Helper: Extract tool argument schema
    # -----------------------------------------------------------

    @staticmethod
    def _extract_tool_args_schema(func_node: ast.FunctionDef) -> dict:
        """Build a JSON Schema dict from a tool function's parameters."""
        _type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
        }
        properties: dict[str, dict[str, str]] = {}
        required: list[str] = []

        for arg in func_node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            prop: dict[str, str] = {}
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    py_type = arg.annotation.id
                    prop["type"] = _type_map.get(py_type, "string")
                else:
                    prop["type"] = "string"
            else:
                prop["type"] = "string"
            properties[arg.arg] = prop
            required.append(arg.arg)

        if not properties:
            return {}

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    # -----------------------------------------------------------
    # AST Helper Methods
    # -----------------------------------------------------------

    @staticmethod
    def _get_call_name(node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    @staticmethod
    def _get_attr_value_name(node: ast.Attribute) -> Optional[str]:
        if isinstance(node.value, ast.Name):
            return node.value.id
        return None

    @staticmethod
    def _extract_keyword_string(call: ast.Call, name: str) -> Optional[str]:
        """Extract a string keyword argument, handling both simple and joined strings."""
        for kw in call.keywords:
            if kw.arg != name:
                continue
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
            # Handle parenthesized multi-line strings: ("part1" "part2")
            if isinstance(kw.value, ast.JoinedStr):
                try:
                    return ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    return ast.unparse(kw.value)
        return None

    @staticmethod
    def _safe_key(name: str) -> str:
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")
