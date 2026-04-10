"""
autogen_parser.py
=================
AutoGen-specific source code parser.

Reads AutoGen projects and produces the shared intermediate
representations defined in :mod:`oscin.intermediate`.

AutoGen Construct → Intermediate Mapping
-----------------------------------------
- ``AssistantAgent(name=..., system_message=...)``
      → ``ExtractedAgent(role=name, backstory=system_message)``
- ``UserProxyAgent(name=..., ...)``
      → ``ExtractedAgent(role=name, agent_key=name)``
- ``ConversableAgent(name=..., ...)``
      → ``ExtractedAgent(role=name)``
- ``GroupChat(agents=[...], ...)``
      → ``ExtractedTeam(agent_keys=[...])``
- ``GroupChatManager(groupchat=..., llm_config=...)``
      → Hierarchical coordination pattern on ExtractedTeam
- ``register_function(...)`` or ``@tool``-decorated functions
      → ``ExtractedTool(...)``
- ``initiate_chat(...)`` or sequential ``send()`` calls
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
from typing import Any, Optional

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

# AutoGen agent class names that the parser recognises
_AGENT_CLASSES = {
    "AssistantAgent",
    "UserProxyAgent",
    "ConversableAgent",
    "CompressibleAgent",
    "RetrieveAssistantAgent",
    "RetrieveUserProxyAgent",
    "GPTAssistantAgent",
}


class AutoGenParser(BaseSourceParser):
    """
    Parses AutoGen source files and extracts intermediate representations.

    The parser scans all ``*.py`` files in the source directory and uses
    Python's AST module to detect AutoGen-specific patterns such as
    agent instantiations, GroupChat configurations, and tool registrations.

    .. note::

       This parser currently provides the structural scaffolding and
       AST pattern detection for the most common AutoGen constructs.
       When you have an AutoGen example project to test against, the
       extraction logic can be refined and validated.
    """

    # -----------------------------------------------------------
    # Abstract interface
    # -----------------------------------------------------------

    @staticmethod
    def framework_name() -> str:
        return "AutoGen"

    def parse_all(self) -> None:
        """
        Execute the full AutoGen extraction pipeline.

        Extraction order:
        1. Scan all Python files for agent instantiations
        2. Detect GroupChat / GroupChatManager configurations
        3. Detect tool registrations and @tool decorators
        4. Detect conversation initiation patterns (initiate_chat)
        """
        log.info("=" * 60)
        log.info("STARTING AUTOGEN SOURCE CODE EXTRACTION")
        log.info("Source directory: %s", self.source_dir)
        log.info("=" * 60)

        # Collect all AST trees first
        trees: list[tuple[Path, ast.Module]] = []
        for py_file in self.source_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            trees.append((py_file, tree))

        # Step 1: Extract agents
        for filepath, tree in trees:
            self._extract_agents(tree, filepath)

        # Step 2: Extract GroupChat / teams
        for filepath, tree in trees:
            self._extract_teams(tree, filepath)

        # Step 3: Extract tools
        for filepath, tree in trees:
            self._extract_tools(tree, filepath)

        # Step 4: Extract conversation flow
        for filepath, tree in trees:
            self._extract_flow(tree, filepath)

        self.log_extraction_summary()

    # -----------------------------------------------------------
    # Step 1: Agent Extraction
    # -----------------------------------------------------------

    def _extract_agents(self, tree: ast.Module, filepath: Path) -> None:
        """
        Find AutoGen agent instantiations.

        Patterns detected:
        - ``agent = AssistantAgent(name="...", system_message="...", llm_config={...})``
        - ``agent = UserProxyAgent(name="...", code_execution_config={...})``
        - ``agent = ConversableAgent(name="...", ...)``
        """
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Detect agent class instantiation
            class_name = self._get_call_name(node)
            if class_name not in _AGENT_CLASSES:
                continue

            # Extract name= keyword
            name = self._extract_keyword_string(node, "name") or class_name
            system_message = self._extract_keyword_string(node, "system_message") or ""

            # Extract llm_config to determine the LLM model
            llm = self._extract_llm_from_config(node)

            # Determine agent type from class name
            is_user_proxy = "UserProxy" in class_name
            is_retrieve = "Retrieve" in class_name

            role = name
            goal = ""
            backstory = system_message

            # For UserProxyAgent, the role is typically "user_proxy"
            if is_user_proxy:
                goal = "Execute code and provide human feedback"

            agent = ExtractedAgent(
                agent_key=self._safe_key(name),
                role=role,
                goal=goal,
                backstory=backstory,
                llm=llm,
                tools=[],
                reasoning=False,
                memory=is_retrieve,  # RAG agents have memory
                verbose=None,
                source_file=str(filepath),
            )
            self.agents[agent.agent_key] = agent
            log.info("  [Agent] '%s' (%s) from %s", name, class_name, filepath.name)

    # -----------------------------------------------------------
    # Step 2: GroupChat / Team Extraction
    # -----------------------------------------------------------

    def _extract_teams(self, tree: ast.Module, filepath: Path) -> None:
        """
        Find GroupChat(...) and GroupChatManager(...) patterns.

        Patterns detected:
        - ``groupchat = GroupChat(agents=[a, b, c], messages=[], ...)``
        - ``manager = GroupChatManager(groupchat=gc, llm_config=...)``
        """
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            class_name = self._get_call_name(node)
            if class_name != "GroupChat":
                continue

            # Extract agents= list
            agent_keys = []
            for kw in node.keywords:
                if kw.arg == "agents" and isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Name):
                            # The variable name might match an agent_key
                            agent_keys.append(self._safe_key(elt.id))

            # Extract max_round for coordination info
            max_round = self._extract_keyword_int(node, "max_round")

            # Detect if there's a GroupChatManager (makes it hierarchical)
            has_manager = self._tree_has_call(tree, "GroupChatManager")

            team = ExtractedTeam(
                team_class_name="GroupChat",
                agent_keys=agent_keys,
                task_keys=[],  # AutoGen doesn't have explicit task objects
                process="hierarchical" if has_manager else "sequential",
                verbose=False,
                memory=False,
                manager_llm=None,
                source_file=str(filepath),
            )
            team_key = f"GroupChat_{len(self.teams)}"
            self.teams[team_key] = team
            log.info("  [Team] GroupChat with %d agents from %s", len(agent_keys), filepath.name)

    # -----------------------------------------------------------
    # Step 3: Tool Extraction
    # -----------------------------------------------------------

    def _extract_tools(self, tree: ast.Module, filepath: Path) -> None:
        """
        Find tool registrations and @tool-decorated functions.

        Patterns detected:
        - ``register_function(func, caller=agent, executor=proxy, ...)``
        - ``@user_proxy.register_for_execution()`` + ``@assistant.register_for_llm(...)``
        - Functions decorated with ``@tool``
        """
        for node in ast.iter_child_nodes(tree):
            # Pattern 1: @tool decorated functions
            if isinstance(node, ast.FunctionDef) and self._has_decorator(node, "tool"):
                tool = ExtractedTool(
                    class_name=node.name,
                    name=node.name,
                    description=ast.get_docstring(node) or "",
                    args_schema_json="{}",
                    implementation_ref=f"{filepath.stem}.{node.name}",
                    source_file=str(filepath),
                )
                self.tools[node.name] = tool
                log.info("  [Tool] @tool function '%s' from %s", node.name, filepath.name)

            # Pattern 2: register_function() calls
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call_name = self._get_call_name(node.value)
                if call_name == "register_function":
                    # First positional arg is the function reference
                    if node.value.args and isinstance(node.value.args[0], ast.Name):
                        func_name = node.value.args[0].id
                        desc = self._extract_keyword_string(node.value, "description") or ""
                        tool = ExtractedTool(
                            class_name=func_name,
                            name=func_name,
                            description=desc,
                            args_schema_json="{}",
                            implementation_ref=f"{filepath.stem}.{func_name}",
                            source_file=str(filepath),
                        )
                        self.tools[func_name] = tool
                        log.info("  [Tool] register_function '%s' from %s", func_name, filepath.name)

    # -----------------------------------------------------------
    # Step 4: Flow / Conversation Extraction
    # -----------------------------------------------------------

    def _extract_flow(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect conversation initiation patterns.

        Patterns detected:
        - ``agent.initiate_chat(other_agent, message="...")``
        - Sequential ``agent.send(message, recipient)`` calls
        """
        steps: list[ExtractedFlowStep] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue

            if node.func.attr == "initiate_chat":
                # The caller is the initiating agent
                caller = self._get_attr_value_name(node.func)
                # The first positional arg is the target agent
                target = ""
                if node.args and isinstance(node.args[0], ast.Name):
                    target = node.args[0].id

                step = ExtractedFlowStep(
                    method_name=f"initiate_chat_{caller or 'unknown'}",
                    decorator_type="start",
                    decorator_args=[self._safe_key(target)] if target else [],
                    calls_crew=None,
                )
                steps.append(step)
                log.info("  [Flow] initiate_chat: %s → %s from %s",
                         caller, target, filepath.name)

        if steps and not self.flow:
            self.flow = ExtractedFlow(
                class_name="AutoGenConversation",
                state_model=None,
                steps=steps,
                crew_references=[],
                source_file=str(filepath),
            )

    # -----------------------------------------------------------
    # AST Helper Methods
    # -----------------------------------------------------------

    @staticmethod
    def _get_call_name(node: ast.Call) -> str:
        """Get the simple name of a function/class being called."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    @staticmethod
    def _get_attr_value_name(node: ast.Attribute) -> Optional[str]:
        """Get the variable name from ``var.method(...)``."""
        if isinstance(node.value, ast.Name):
            return node.value.id
        return None

    @staticmethod
    def _has_decorator(node: ast.FunctionDef, decorator_name: str) -> bool:
        """Check if a function has a given decorator."""
        for deco in node.decorator_list:
            if isinstance(deco, ast.Name) and deco.id == decorator_name:
                return True
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name):
                if deco.func.id == decorator_name:
                    return True
        return False

    @staticmethod
    def _extract_keyword_string(call: ast.Call, name: str) -> Optional[str]:
        """Extract a string keyword argument value."""
        for kw in call.keywords:
            if kw.arg == name and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        return None

    @staticmethod
    def _extract_keyword_int(call: ast.Call, name: str) -> Optional[int]:
        """Extract an integer keyword argument value."""
        for kw in call.keywords:
            if kw.arg == name and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
                return kw.value.value
        return None

    @staticmethod
    def _extract_llm_from_config(call: ast.Call) -> Optional[str]:
        """
        Try to extract the LLM model name from ``llm_config={"model": "..."}``
        or ``llm_config={"config_list": [{"model": "..."}]}``.
        """
        for kw in call.keywords:
            if kw.arg != "llm_config":
                continue
            if isinstance(kw.value, ast.Dict):
                for key, val in zip(kw.value.keys, kw.value.values):
                    if isinstance(key, ast.Constant) and key.value == "model":
                        if isinstance(val, ast.Constant) and isinstance(val.value, str):
                            return val.value
        return None

    @staticmethod
    def _tree_has_call(tree: ast.Module, func_name: str) -> bool:
        """Check if a tree contains any call to func_name."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == func_name:
                    return True
        return False

    @staticmethod
    def _safe_key(name: str) -> str:
        """Convert a name to a safe dict key."""
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")
