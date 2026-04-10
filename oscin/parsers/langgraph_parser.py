"""
langgraph_parser.py
===================
LangGraph-specific source code parser.

Reads LangGraph projects and produces the shared intermediate
representations defined in :mod:`oscin.intermediate`.

LangGraph Construct → Intermediate Mapping
--------------------------------------------
- ``StateGraph(State)``
      → ``ExtractedFlow(class_name=..., state_model="State")``
- ``graph.add_node("name", func)``
      → ``ExtractedFlowStep(method_name="name", decorator_type="listen")``
- ``graph.set_entry_point("name")`` or ``graph.add_edge(START, "name")``
      → ``ExtractedFlowStep(decorator_type="start")``
- ``graph.add_edge("a", "b")``
      → nextStep connectivity between steps
- ``graph.add_conditional_edges("node", func, {...})``
      → ``ExtractedFlowStep(decorator_type="router")``
      with return_values from the mapping dict
- ``graph.add_edge("name", END)``
      → marks step as an EndStep
- ``ToolNode([tools])``
      → ``ExtractedTool(...)`` for each tool in the list
- Functions used as nodes that invoke agents
      → ``ExtractedAgent(...)``

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


class LangGraphParser(BaseSourceParser):
    """
    Parses LangGraph source files and extracts intermediate representations.

    LangGraph applications are graph-based: nodes are processing functions
    and edges define the execution flow.  This maps naturally to the
    ontology's Orchestration / WorkflowPattern / WorkflowStep model.

    The parser scans all ``*.py`` files in the source directory and uses
    Python's AST module to detect ``StateGraph`` construction patterns
    including ``add_node``, ``add_edge``, ``add_conditional_edges``,
    ``set_entry_point``, and ``set_finish_point``.

    .. note::

       This parser provides the structural scaffolding and AST pattern
       detection for the most common LangGraph constructs.  When you
       have a LangGraph example project to test against, the extraction
       logic can be refined and validated.
    """

    # -----------------------------------------------------------
    # Abstract interface
    # -----------------------------------------------------------

    @staticmethod
    def framework_name() -> str:
        return "LangGraph"

    def parse_all(self) -> None:
        """
        Execute the full LangGraph extraction pipeline.

        Extraction order:
        1. Scan for StateGraph instantiation and state model
        2. Extract add_node() calls → flow steps
        3. Extract add_edge() / add_conditional_edges() → step connectivity
        4. Detect agent invocations inside node functions
        5. Detect ToolNode and tool registrations
        """
        log.info("=" * 60)
        log.info("STARTING LANGGRAPH SOURCE CODE EXTRACTION")
        log.info("Source directory: %s", self.source_dir)
        log.info("=" * 60)

        # Collect all source files
        sources: list[tuple[Path, str, ast.Module]] = []
        for py_file in self.source_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            sources.append((py_file, source, tree))

        # --- Graph structure extraction ---
        # We need to track:
        #   - nodes (add_node calls)
        #   - edges (add_edge calls)
        #   - conditional edges (add_conditional_edges calls)
        #   - entry/finish points
        nodes: dict[str, _NodeInfo] = {}
        edges: list[tuple[str, str]] = []                  # (from, to)
        conditional_edges: list[_ConditionalEdge] = []
        entry_points: list[str] = []
        finish_points: list[str] = []
        state_model: Optional[str] = None
        graph_class_name: Optional[str] = None
        graph_source_file: str = ""

        for filepath, source, tree in sources:
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                # --- StateGraph(...) instantiation ---
                call_name = self._get_call_name(node)
                if call_name == "StateGraph":
                    graph_class_name = "StateGraph"
                    graph_source_file = str(filepath)
                    # Extract state model: StateGraph(State)
                    if node.args and isinstance(node.args[0], ast.Name):
                        state_model = node.args[0].id
                    log.info("  [Graph] Found StateGraph(state=%s) in %s",
                             state_model, filepath.name)
                    continue

                # --- Method calls on graph object ---
                if not isinstance(node.func, ast.Attribute):
                    continue
                method_name = node.func.attr

                # --- add_node("name", func) ---
                if method_name == "add_node":
                    node_name = self._extract_first_string_arg(node)
                    func_ref = self._extract_second_arg_name(node)
                    if node_name:
                        nodes[node_name] = _NodeInfo(
                            name=node_name,
                            func_ref=func_ref,
                            source_file=str(filepath),
                        )
                        log.info("    [Node] add_node('%s', %s)", node_name, func_ref or "?")

                # --- set_entry_point("name") ---
                elif method_name == "set_entry_point":
                    ep = self._extract_first_string_arg(node)
                    if ep:
                        entry_points.append(ep)
                        log.info("    [Entry] set_entry_point('%s')", ep)

                # --- set_finish_point("name") ---
                elif method_name == "set_finish_point":
                    fp = self._extract_first_string_arg(node)
                    if fp:
                        finish_points.append(fp)
                        log.info("    [Finish] set_finish_point('%s')", fp)

                # --- add_edge("a", "b") or add_edge(START, "b") ---
                elif method_name == "add_edge":
                    from_node = self._extract_arg_string_or_name(node, 0)
                    to_node = self._extract_arg_string_or_name(node, 1)
                    if from_node and to_node:
                        # Handle START/END constants
                        if from_node == "START":
                            entry_points.append(to_node)
                            log.info("    [Edge] START → '%s'", to_node)
                        elif to_node == "END":
                            finish_points.append(from_node)
                            log.info("    [Edge] '%s' → END", from_node)
                        else:
                            edges.append((from_node, to_node))
                            log.info("    [Edge] '%s' → '%s'", from_node, to_node)

                # --- add_conditional_edges("node", func, {"val": "target", ...}) ---
                elif method_name == "add_conditional_edges":
                    source_node = self._extract_first_string_arg(node)
                    routing_func = self._extract_second_arg_name(node)
                    mapping = self._extract_third_arg_dict(node)
                    if source_node:
                        ce = _ConditionalEdge(
                            source_node=source_node,
                            routing_func=routing_func,
                            mapping=mapping,
                        )
                        conditional_edges.append(ce)
                        log.info("    [ConditionalEdge] '%s' via %s → %s",
                                 source_node, routing_func or "?", mapping)

        # --- Extract agents from node functions ---
        for filepath, source, tree in sources:
            self._extract_agents_from_functions(tree, filepath, nodes)

        # --- Extract tools (ToolNode patterns) ---
        for filepath, source, tree in sources:
            self._extract_tools(tree, filepath)

        # --- Build the ExtractedFlow from graph structure ---
        if nodes:
            steps = self._build_flow_steps(
                nodes, edges, conditional_edges, entry_points, finish_points
            )
            self.flow = ExtractedFlow(
                class_name=graph_class_name or "LangGraph",
                state_model=state_model,
                steps=steps,
                crew_references=[],
                source_file=graph_source_file,
            )
            log.info("  [Flow] Built flow with %d steps", len(steps))

        self.log_extraction_summary()

    # -----------------------------------------------------------
    # Agent Extraction from Node Functions
    # -----------------------------------------------------------

    def _extract_agents_from_functions(
        self,
        tree: ast.Module,
        filepath: Path,
        nodes: dict[str, _NodeInfo],
    ) -> None:
        """
        Detect agent invocations inside node functions.

        Patterns detected:
        - ``ChatOpenAI(model="...")`` or similar LLM calls inside functions
          used as graph nodes
        - ``model.invoke(...)`` patterns
        - Functions that call ``chain.invoke(...)``
        """
        # Build a set of function names used as graph nodes
        node_func_names = {
            info.func_ref for info in nodes.values() if info.func_ref
        }

        for item in ast.iter_child_nodes(tree):
            if not isinstance(item, ast.FunctionDef):
                continue
            if item.name not in node_func_names:
                continue

            # This function is used as a graph node — check for LLM calls
            llm_model = self._find_llm_in_function(item)

            agent = ExtractedAgent(
                agent_key=self._safe_key(item.name),
                role=item.name,
                goal=ast.get_docstring(item) or "",
                backstory="",
                llm=llm_model,
                tools=[],
                source_file=str(filepath),
            )
            self.agents[agent.agent_key] = agent
            log.info("  [Agent] Node function '%s' (llm: %s) from %s",
                     item.name, llm_model or "unknown", filepath.name)

    # -----------------------------------------------------------
    # Tool Extraction
    # -----------------------------------------------------------

    def _extract_tools(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect ToolNode patterns and @tool-decorated functions.

        Patterns detected:
        - ``ToolNode([tool_a, tool_b])``
        - Functions decorated with ``@tool``
        """
        for node in ast.iter_child_nodes(tree):
            # @tool decorated functions
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

        # ToolNode([...]) calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if self._get_call_name(node) == "ToolNode":
                    if node.args and isinstance(node.args[0], ast.List):
                        for elt in node.args[0].elts:
                            if isinstance(elt, ast.Name):
                                if elt.id not in self.tools:
                                    tool = ExtractedTool(
                                        class_name=elt.id,
                                        name=elt.id,
                                        description="",
                                        args_schema_json="{}",
                                        implementation_ref=f"{filepath.stem}.{elt.id}",
                                        source_file=str(filepath),
                                    )
                                    self.tools[elt.id] = tool
                                    log.info("  [Tool] ToolNode reference '%s' from %s",
                                             elt.id, filepath.name)

    # -----------------------------------------------------------
    # Flow Step Construction
    # -----------------------------------------------------------

    def _build_flow_steps(
        self,
        nodes: dict[str, _NodeInfo],
        edges: list[tuple[str, str]],
        conditional_edges: list[_ConditionalEdge],
        entry_points: list[str],
        finish_points: list[str],
    ) -> list[ExtractedFlowStep]:
        """
        Convert the graph structure into ExtractedFlowStep instances.
        """
        # Determine which nodes are conditional (routers)
        router_sources = {ce.source_node for ce in conditional_edges}

        # Build outgoing edge map for regular edges
        outgoing: dict[str, list[str]] = {name: [] for name in nodes}
        for frm, to in edges:
            if frm in outgoing:
                outgoing[frm].append(to)

        steps: list[ExtractedFlowStep] = []

        for name, info in nodes.items():
            # Determine decorator type
            if name in entry_points:
                dec_type = "start"
            elif name in router_sources:
                dec_type = "router"
            else:
                dec_type = "listen"

            # Build decorator_args (what this step listens to)
            incoming = [frm for frm, to in edges if to == name]
            # Also add conditional edges that target this node
            for ce in conditional_edges:
                for _val, target in ce.mapping.items():
                    if target == name and ce.source_node not in incoming:
                        incoming.append(ce.source_node)

            # For routers, extract return values from the conditional edge mapping
            return_values: list[str] = []
            function_body = ""
            if dec_type == "router":
                for ce in conditional_edges:
                    if ce.source_node == name:
                        return_values = list(ce.mapping.keys())
                        function_body = f"routing_function: {ce.routing_func or 'unknown'}"

            step = ExtractedFlowStep(
                method_name=name,
                decorator_type=dec_type,
                decorator_args=incoming if dec_type == "listen" else [],
                calls_crew=None,
                return_values=return_values,
                function_body=function_body,
            )
            steps.append(step)

        return steps

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
    def _extract_first_string_arg(node: ast.Call) -> Optional[str]:
        """Extract the first positional argument if it's a string constant."""
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return node.args[0].value
        return None

    @staticmethod
    def _extract_second_arg_name(node: ast.Call) -> Optional[str]:
        """Extract the second positional argument if it's a Name."""
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Name):
            return node.args[1].id
        return None

    @staticmethod
    def _extract_arg_string_or_name(node: ast.Call, idx: int) -> Optional[str]:
        """Extract a positional arg as string constant or Name identifier."""
        if idx >= len(node.args):
            return None
        arg = node.args[idx]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        if isinstance(arg, ast.Name):
            return arg.id
        return None

    @staticmethod
    def _extract_third_arg_dict(node: ast.Call) -> dict[str, str]:
        """Extract the third positional argument if it's a dict literal."""
        if len(node.args) < 3:
            return {}
        arg = node.args[2]
        if not isinstance(arg, ast.Dict):
            return {}
        result = {}
        for key, val in zip(arg.keys, arg.values):
            if isinstance(key, ast.Constant) and isinstance(val, ast.Constant):
                result[str(key.value)] = str(val.value)
            elif isinstance(key, ast.Constant) and isinstance(val, ast.Name):
                result[str(key.value)] = val.id
        return result

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
    def _find_llm_in_function(func_node: ast.FunctionDef) -> Optional[str]:
        """
        Search a function body for LLM instantiation patterns like:
        - ChatOpenAI(model="gpt-4")
        - ChatAnthropic(model="claude-3")
        """
        llm_classes = {"ChatOpenAI", "ChatAnthropic", "ChatOllama", "AzureChatOpenAI"}
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in llm_classes:
                    for kw in node.keywords:
                        if kw.arg == "model" and isinstance(kw.value, ast.Constant):
                            return str(kw.value.value)
        return None

    @staticmethod
    def _safe_key(name: str) -> str:
        """Convert a name to a safe dict key."""
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")


# -----------------------------------------------------------
# Private helper dataclasses
# -----------------------------------------------------------

class _NodeInfo:
    """Tracks information about a graph node during extraction."""
    __slots__ = ("name", "func_ref", "source_file")

    def __init__(self, name: str, func_ref: Optional[str], source_file: str):
        self.name = name
        self.func_ref = func_ref
        self.source_file = source_file


class _ConditionalEdge:
    """Tracks information about a conditional edge during extraction."""
    __slots__ = ("source_node", "routing_func", "mapping")

    def __init__(self, source_node: str, routing_func: Optional[str], mapping: dict[str, str]):
        self.source_node = source_node
        self.routing_func = routing_func
        self.mapping = mapping
