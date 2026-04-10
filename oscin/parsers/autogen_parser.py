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
- ``RoundRobinGroupChat(participants=[...])``
      → ``ExtractedTeam(agent_keys=[...])``
- Any plain functions in scope
      → ``ExtractedTool(...)``
- ``team.run(...)``
      → ``ExtractedFlow`` / ``ExtractedFlowStep``

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import ast
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
        log.info("STARTING AUTOGEN V0.4 SOURCE CODE EXTRACTION")
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
        self.llm_clients = {}

        for filepath, tree in trees:
            self._extract_llms(tree, filepath)

        for filepath, tree in trees:
            self._extract_tools(tree, filepath)

        for filepath, tree in trees:
            self._extract_agents(tree, filepath)

        for filepath, tree in trees:
            self._extract_teams(tree, filepath)

        for filepath, tree in trees:
            self._extract_flow(tree, filepath)

        self.log_extraction_summary()

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

    def _extract_agents(self, tree: ast.Module, filepath: Path) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            class_name = self._get_call_name(node)
            if class_name not in _AGENT_CLASSES:
                continue

            name = self._extract_keyword_string(node, "name") or class_name
            system_message = self._extract_keyword_string(node, "system_message") or ""
            
            llm = None
            for kw in node.keywords:
                if kw.arg == "model_client" and isinstance(kw.value, ast.Name):
                    llm = self.llm_clients.get(kw.value.id)

            tools = []
            for kw in node.keywords:
                if kw.arg == "tools" and isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Name):
                            tools.append(elt.id)

            agent = ExtractedAgent(
                agent_key=self._safe_key(name),
                role=name,
                goal="",
                backstory=system_message,
                llm=llm,
                tools=tools,
                reasoning=False,
                memory=False,
                verbose=None,
                source_file=str(filepath),
            )
            self.agents[agent.agent_key] = agent
            log.info("  [Agent] '%s' from %s", name, filepath.name)

    def _extract_tools(self, tree: ast.Module, filepath: Path) -> None:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if node.name == "main":
                    continue
                tool = ExtractedTool(
                    class_name=node.name,
                    name=node.name,
                    description=ast.get_docstring(node) or "",
                    args_schema_json="{}",
                    implementation_ref=f"{filepath.stem}.{node.name}",
                    source_file=str(filepath),
                )
                self.tools[node.name] = tool
                log.info("  [Tool] '%s' from %s", node.name, filepath.name)

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
                            # Adding literal var name but capitalized to match "name=" typical cases roughly
                            # In thesis chapter 7, this limitation is noted.
                            # Usually the parser would map elt.id directly if that matches agent_keys string in scope
                            key = self._safe_key(elt.id)
                            # Provide basic Title Case guess matching CrewAI strings
                            guess_key = "_".join([w.capitalize() for w in key.split("_")])
                            agent_keys.append(guess_key)

            team = ExtractedTeam(
                team_class_name=class_name,
                agent_keys=agent_keys,
                task_keys=[],
                process="sequential" if class_name == "RoundRobinGroupChat" else "hierarchical",
                verbose=False,
                memory=False,
                manager_llm=None,
                source_file=str(filepath),
            )
            team_key = f"{class_name}_{len(self.teams)}"
            self.teams[team_key] = team
            log.info("  [Team] %s with %d agents from %s", class_name, len(agent_keys), filepath.name)

    def _extract_flow(self, tree: ast.Module, filepath: Path) -> None:
        steps = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "run":
                    caller = self._get_attr_value_name(node.func)
                    step = ExtractedFlowStep(
                        method_name=f"run_{caller or 'unknown'}",
                        decorator_type="start",
                        decorator_args=[],
                        calls_crew=caller, 
                    )
                    steps.append(step)
                    log.info("  [Flow] run: %s from %s", caller, filepath.name)
        
        if steps and not self.flow:
            self.flow = ExtractedFlow(
                class_name="AutoGenV04Flow",
                state_model=None,
                steps=steps,
                crew_references=[],
                source_file=str(filepath),
            )

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
        for kw in call.keywords:
            if kw.arg == name and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        return None

    @staticmethod
    def _safe_key(name: str) -> str:
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")
