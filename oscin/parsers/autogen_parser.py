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
    ExtractedTeam,
    ExtractedTool,
)

log = logging.getLogger("oscin")

_AGENT_CLASSES = {"AssistantAgent"}


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
                code_cells = [cell["source"] for cell in nb.cells if cell.cell_type == "code"]
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
                            log.info("  [LLM] %s = OpenAIChatCompletionClient(model='%s') in %s",
                                     target.id, model, filepath.name)

    # -----------------------------------------------------------
    # FunctionTool Detection
    # -----------------------------------------------------------

    def _extract_function_tools(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect ``FunctionTool(func, description="...")`` wrapping patterns.

        Builds a mapping from variable name to (function_name, description)
        so that agent tool references can be resolved.
        """
        for node in ast.iter_child_nodes(tree):
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
                log.info("  [FunctionTool] %s = FunctionTool(%s, desc='%s') in %s",
                         target.id, func_name, description[:60], filepath.name)

    # -----------------------------------------------------------
    # Tool Extraction
    # -----------------------------------------------------------

    def _extract_tools(self, tree: ast.Module, filepath: Path) -> None:
        """Extract tool functions. Enhances with FunctionTool descriptions."""
        for node in ast.iter_child_nodes(tree):
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
                log.info("  [Tool] '%s' (desc from %s) from %s",
                         node.name,
                         "FunctionTool" if ft_description else "docstring",
                         filepath.name)

    # -----------------------------------------------------------
    # Agent Extraction
    # -----------------------------------------------------------

    def _extract_agents(self, tree: ast.Module, filepath: Path) -> None:
        """Extract AssistantAgent instantiations with variable-to-key mapping."""
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Call):
                continue

            class_name = self._get_call_name(node.value)
            if class_name not in _AGENT_CLASSES:
                continue

            name = self._extract_keyword_string(node.value, "name") or class_name
            system_message = self._extract_keyword_string(node.value, "system_message") or ""

            llm = None
            for kw in node.value.keywords:
                if kw.arg == "model_client" and isinstance(kw.value, ast.Name):
                    llm = self.llm_clients.get(kw.value.id)

            # Resolve tool references through FunctionTool mapping
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

            # Heuristic: split system_message into goal and backstory
            goal, backstory = self._split_system_message(system_message)

            agent_key = self._safe_key(name)
            agent = ExtractedAgent(
                agent_key=agent_key,
                role=name,
                goal=goal,
                backstory=backstory,
                llm=llm,
                tools=tools,
                reasoning=False,
                memory=False,
                verbose=None,
                source_file=str(filepath),
            )
            self.agents[agent_key] = agent

            # Store variable-to-key mapping for team participant resolution
            self._var_to_agent_key[target.id] = agent_key
            log.info("  [Agent] '%s' (var=%s, llm=%s, tools=%s) from %s",
                     name, target.id, llm or "unknown", tools or "none", filepath.name)

    # -----------------------------------------------------------
    # Team Extraction
    # -----------------------------------------------------------

    def _extract_teams(self, tree: ast.Module, filepath: Path) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            class_name = self._get_call_name(node)
            if class_name not in ["RoundRobinGroupChat", "SelectorGroupChat"]:
                continue

            agent_keys = []
            for kw in node.keywords:
                if kw.arg == "participants" and isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Name):
                            # Resolve through variable-to-agent mapping
                            if elt.id in self._var_to_agent_key:
                                agent_keys.append(self._var_to_agent_key[elt.id])
                            else:
                                # Fallback: use the variable name as-is
                                agent_keys.append(self._safe_key(elt.id))

            # Extract max_turns
            max_turns = None
            for kw in node.keywords:
                if kw.arg == "max_turns" and isinstance(kw.value, ast.Constant):
                    if isinstance(kw.value.value, int):
                        max_turns = kw.value.value

            team = ExtractedTeam(
                team_class_name=class_name,
                agent_keys=agent_keys,
                task_keys=[],
                process="sequential" if class_name == "RoundRobinGroupChat" else "hierarchical",
                verbose=False,
                memory=False,
                manager_llm=None,
                max_turns=max_turns,
                source_file=str(filepath),
            )
            team_key = f"{class_name}_{len(self.teams)}"
            self.teams[team_key] = team
            log.info("  [Team] %s with %d agents (max_turns=%s) from %s",
                     class_name, len(agent_keys), max_turns, filepath.name)

    # -----------------------------------------------------------
    # Flow Extraction
    # -----------------------------------------------------------

    def _extract_flow(self, tree: ast.Module, filepath: Path) -> None:
        steps = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("run", "run_stream"):
                    caller = self._get_attr_value_name(node.func)
                    step = ExtractedFlowStep(
                        method_name=f"run_{caller or 'unknown'}",
                        decorator_type="start",
                        decorator_args=[],
                        calls_crew=caller,
                    )
                    steps.append(step)
                    log.info("  [Flow] %s: %s from %s",
                             node.func.attr, caller, filepath.name)

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
