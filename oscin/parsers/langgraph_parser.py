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
      → ``ExtractedFlowStep(method_name="name", step_type="regular")``
- ``graph.set_entry_point("name")`` or ``graph.add_edge(START, "name")``
      → ``ExtractedFlowStep(step_type="start")``
- ``graph.add_edge("a", "b")``
      → nextStep connectivity between steps
- ``graph.add_conditional_edges("node", func, {...})``
      → ``ExtractedFlowStep(step_type="router")``
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
from oscin.parsers import ast_utils

import nbformat

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

_LLM_CLASSES = {"ChatOpenAI", "ChatAnthropic", "ChatOllama", "AzureChatOpenAI"}


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

        # Collect all source files (.py and .ipynb)
        sources: list[tuple[Path, str, ast.Module]] = []
        for py_file in self.source_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(py_file))
                sources.append((py_file, source, tree))
            except SyntaxError:
                log.warning("SyntaxError parsing %s — skipping", py_file.name)

        for nb_file in self.source_dir.rglob("*.ipynb"):
            if ".ipynb_checkpoints" in str(nb_file):
                continue
            try:
                with open(nb_file, "r", encoding="utf-8") as f:
                    nb = nbformat.read(f, as_version=4)
                code_cells = []
                for cell in nb.cells:
                    if cell.cell_type != "code":
                        continue
                    # Filter out IPython magics and shell commands
                    lines = []
                    for line in cell["source"].splitlines():
                        stripped = line.strip()
                        if stripped.startswith(("%", "!")):
                            continue
                        lines.append(line)
                    cell_source = "\n".join(lines).strip()
                    if cell_source:
                        code_cells.append(cell_source)
                source = "\n\n".join(code_cells)
                tree = ast.parse(source, filename=str(nb_file))
                sources.append((nb_file, source, tree))
                log.info(
                    "  [Notebook] Parsed %s (%d code cells)",
                    nb_file.name,
                    len(code_cells),
                )
            except Exception as e:
                log.warning("Failed to parse notebook %s: %s", nb_file.name, e)

        # --- Pre-pass: collect module-level LLM definitions ---
        # Tracks variable_name → model string, e.g. {"llm": "gpt-4o"}
        self._module_llms: dict[str, str] = {}
        # Tracks variable_name → set of tool names bound via .bind_tools()
        self._bound_tools: dict[str, set[str]] = {}
        # Tracks ToolNode node names (infrastructure, not agents)
        self._tool_node_names: set[str] = set()
        # Tracks variable_name → ToolNode (to detect add_node("tools", tool_node))
        self._tool_node_vars: set[str] = set()
        for filepath, source, tree in sources:
            self._extract_module_level_llms(tree, filepath)
            self._extract_bind_tools(tree, filepath)

        # --- Graph structure extraction ---
        # We need to track:
        #   - nodes (add_node calls)
        #   - edges (add_edge calls)
        #   - conditional edges (add_conditional_edges calls)
        #   - entry/finish points
        nodes: dict[str, _NodeInfo] = {}
        edges: list[tuple[str, str]] = []  # (from, to)
        conditional_edges: list[_ConditionalEdge] = []
        entry_points: list[str] = []
        finish_points: list[str] = []
        state_model: Optional[str] = None
        graph_class_name: Optional[str] = None
        graph_source_file: str = ""

        # --- Pre-pass: detect ToolNode variable assignments ---
        # e.g. tool_node = ToolNode(tools=tools) or tool_node = ToolNode([add, sub])
        for filepath, source, tree in sources:
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name) and isinstance(
                        node.value, ast.Call
                    ):
                        if ast_utils.get_call_name(node.value) == "ToolNode":
                            self._tool_node_vars.add(target.id)

        for filepath, source, tree in sources:
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                # --- StateGraph(...) instantiation ---
                call_name = ast_utils.get_call_name(node)
                if call_name == "StateGraph":
                    graph_class_name = "StateGraph"
                    graph_source_file = str(filepath)
                    # Extract state model: StateGraph(State)
                    if node.args and isinstance(node.args[0], ast.Name):
                        state_model = node.args[0].id
                    log.info(
                        "  [Graph] Found StateGraph(state=%s) in %s",
                        state_model,
                        filepath.name,
                    )
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
                        # Check if this node is a ToolNode (infrastructure, not an agent)
                        is_tool_node = False
                        if func_ref and func_ref in self._tool_node_vars:
                            is_tool_node = True
                        elif func_ref == "ToolNode":
                            is_tool_node = True
                        # Also detect inline: add_node("tools", ToolNode(tools))
                        if len(node.args) >= 2 and isinstance(node.args[1], ast.Call):
                            if ast_utils.get_call_name(node.args[1]) == "ToolNode":
                                is_tool_node = True

                        if is_tool_node:
                            self._tool_node_names.add(node_name)
                            log.info(
                                "    [ToolNode] add_node('%s', ToolNode) — skipping as agent",
                                node_name,
                            )
                        else:
                            nodes[node_name] = _NodeInfo(
                                name=node_name,
                                func_ref=func_ref,
                                source_file=str(filepath),
                            )
                            log.info(
                                "    [Node] add_node('%s', %s)",
                                node_name,
                                func_ref or "?",
                            )

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
                # Also handles: add_conditional_edges("node", func, ["target1", END])
                elif method_name == "add_conditional_edges":
                    source_node = self._extract_first_string_arg(node)
                    routing_func = self._extract_second_arg_name(node)
                    mapping = self._extract_mapping_arg(node)
                    if source_node:
                        ce = _ConditionalEdge(
                            source_node=source_node,
                            routing_func=routing_func,
                            mapping=mapping,
                        )
                        conditional_edges.append(ce)
                        log.info(
                            "    [ConditionalEdge] '%s' via %s → %s",
                            source_node,
                            routing_func or "?",
                            mapping,
                        )

        # --- Extract agents from node functions ---
        for filepath, source, tree in sources:
            self._extract_agents_from_functions(tree, filepath, nodes)

        # --- Create stub agents for nodes without a matched function ---
        # Skip ToolNode nodes — they are infrastructure, not agents.
        for name, info in nodes.items():
            agent_key = ast_utils.safe_key(name)
            if agent_key not in self.agents:
                if name in self._tool_node_names:
                    log.info("  [Agent] Skipping stub for ToolNode '%s'", name)
                    continue
                # Use module-level LLM as fallback
                llm_model = (
                    next(iter(self._module_llms.values()), None)
                    if self._module_llms
                    else None
                )
                agent = ExtractedAgent(
                    agent_key=agent_key,
                    role=name,
                    goal="",
                    backstory="",
                    llm=llm_model,
                    tools=[],
                    source_file=info.source_file,
                )
                self.agents[agent_key] = agent
                log.info(
                    "  [Agent] Stub for node '%s' (no matching function, llm: %s)",
                    name,
                    llm_model or "unknown",
                )

        # --- Extract tools (ToolNode patterns + StructuredTool) ---
        for filepath, source, tree in sources:
            self._extract_tools(tree, filepath)

        # --- Extract Pydantic models (structured output schemas) ---
        for filepath, source, tree in sources:
            self._extract_pydantic_models(tree, filepath)

        # --- Resolve empty conditional edge mappings from routing functions ---
        # When add_conditional_edges("node", func) has no explicit mapping,
        # the routing function returns node names directly. Try to infer
        # the targets from the function's return type annotation or body.
        for ce in conditional_edges:
            if not ce.mapping and ce.routing_func:
                inferred = self._infer_router_targets(sources, ce.routing_func)
                if inferred:
                    ce.mapping = {t: t for t in inferred}
                    log.info(
                        "    [ConditionalEdge] Inferred targets for '%s': %s",
                        ce.source_node,
                        inferred,
                    )

        # --- Extract TypedDict state fields ---
        state_fields: dict[str, str] = {}
        if state_model:
            for filepath, source, tree in sources:
                state_fields = self._extract_typeddict_fields(tree, state_model)
                if state_fields:
                    log.info(
                        "  [State] Extracted %d fields from %s: %s",
                        len(state_fields),
                        state_model,
                        list(state_fields.keys()),
                    )
                    break

        # --- B1: Create tasks for each agent node ---
        for agent_key, agent in self.agents.items():
            task_desc = ""
            expected_output = ""
            node_name = agent.role
            for filepath, source, tree in sources:
                candidate_desc = self._extract_human_message_from_function(
                    tree, nodes.get(node_name)
                )
                if candidate_desc and not task_desc:
                    task_desc = candidate_desc

                candidate_keys = self._extract_returned_state_keys(
                    tree, nodes.get(node_name)
                )
                if candidate_keys and not expected_output:
                    expected_output = ",".join(candidate_keys)

                if task_desc and expected_output:
                    break

            if not task_desc:
                task_desc = f"Perform {agent.role} responsibilities"

            task = ExtractedTask(
                task_key=f"task_{agent_key}",
                description=task_desc,
                expected_output=expected_output,
                agent_key=agent_key,
                delegation_strategy="TopologyDetermined",  # B2
                source_file=agent.source_file,
            )
            self.tasks[task.task_key] = task
            log.info(
                "  [Task] Created for agent '%s': '%s...'", agent_key, task_desc[:60]
            )

        # --- B5: Detect memory from graph.compile() ---
        memory_type = ""
        memory_persistence = ""
        for filepath, source, tree in sources:
            mem_info = self._extract_compile_memory(tree)
            if mem_info:
                memory_type = mem_info.get("type", "")
                memory_persistence = mem_info.get("persistence", "")
                log.info(
                    "  [Memory] Detected %s (persistence: %s)",
                    memory_type,
                    memory_persistence,
                )
                break

        # --- B6: Detect interrupt() calls in node functions ---
        for filepath, source, tree in sources:
            self._detect_interrupts(tree, filepath, nodes)

        # --- B3: Create Team from StateGraph ---
        if nodes:
            agent_keys = [k for k in self.agents.keys()]
            task_keys = [k for k in self.tasks.keys()]

            # B4: Classify coordination pattern from topology
            coord_pattern = self._classify_coordination_pattern(
                nodes, edges, conditional_edges, entry_points
            )

            team = ExtractedTeam(
                team_class_name=graph_class_name or "StateGraph",
                agent_keys=agent_keys,
                task_keys=task_keys,
                process="sequential",
                coordination_pattern=coord_pattern,
                termination_conditions=[{"type": "Routing"}],  # B7: RoutingTermination
                source_file=graph_source_file,
                memory=bool(memory_type),
            )
            team_key = f"langgraph_team_{len(self.teams)}"
            self.teams[team_key] = team
            log.info(
                "  [Team] Created with %d agents, pattern=%s",
                len(agent_keys),
                coord_pattern,
            )

        # --- Build the ExtractedFlow from graph structure ---
        if nodes:
            steps = self._build_flow_steps(
                nodes,
                edges,
                conditional_edges,
                entry_points,
                finish_points,
                sources,
            )
            self.flow = ExtractedFlow(
                class_name=graph_class_name or "LangGraph",
                state_model=state_model,
                steps=steps,
                crew_references=[],
                source_file=graph_source_file,
                state_fields=state_fields,
            )
            log.info("  [Flow] Built flow with %d steps", len(steps))

        # --- Extract create_react_agent calls ---
        for filepath, source, tree in sources:
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and ast_utils.get_call_name(node) == "create_react_agent"
                ):
                    model = ""
                    tools = []

                    if node.args:
                        if len(node.args) >= 1:
                            if isinstance(node.args[0], ast.Name):
                                model = node.args[0].id
                                if model in self._module_llms:
                                    model = self._module_llms[model]
                        if len(node.args) >= 2:
                            if isinstance(node.args[1], ast.List):
                                for elt in node.args[1].elts:
                                    if isinstance(elt, ast.Name):
                                        tools.append(elt.id)
                            elif isinstance(node.args[1], ast.Name):
                                tools = list(
                                    self._resolve_tool_list_variable(
                                        tree, node.args[1].id
                                    )
                                )

                    for kw in node.keywords:
                        if kw.arg == "model" and isinstance(kw.value, ast.Name):
                            model = kw.value.id
                            if model in self._module_llms:
                                model = self._module_llms[model]
                        elif kw.arg == "tools":
                            if isinstance(kw.value, ast.List):
                                for elt in kw.value.elts:
                                    if isinstance(elt, ast.Name):
                                        tools.append(elt.id)
                            elif isinstance(kw.value, ast.Name):
                                tools = list(
                                    self._resolve_tool_list_variable(tree, kw.value.id)
                                )

                    agent_key = f"react_agent_{len(self.agents)}"
                    agent = ExtractedAgent(
                        agent_key=agent_key,
                        role="react_agent",
                        goal="React Agent",
                        backstory="",
                        llm=model or next(iter(self._module_llms.values()), None)
                        if not model and self._module_llms
                        else model,
                        tools=tools,
                        source_file=str(filepath),
                    )
                    agent.reasoning = True
                    agent.reasoning_origin = "FrameworkManaged"
                    self.agents[agent_key] = agent

                    task_key = f"task_{agent_key}"
                    task = ExtractedTask(
                        task_key=task_key,
                        description="Execute React Agent tasks",
                        expected_output="",
                        agent_key=agent_key,
                        delegation_strategy="TopologyDetermined",
                        source_file=str(filepath),
                    )
                    self.tasks[task_key] = task

                    team_key = f"langgraph_team_{len(self.teams)}"
                    team = ExtractedTeam(
                        team_class_name="ReactAgentTeam",
                        agent_keys=[agent_key],
                        task_keys=[task_key],
                        process="sequential",
                        coordination_pattern="ReActLoop",
                        termination_conditions=[{"type": "Routing"}],
                        source_file=str(filepath),
                        memory=False,
                    )
                    self.teams[team_key] = team
                    log.info(
                        "  [ReAct] Extracted create_react_agent in %s", filepath.name
                    )

        self.log_extraction_summary()

    # -----------------------------------------------------------
    # B1: HumanMessage Extraction from Node Functions
    # -----------------------------------------------------------

    def _extract_returned_state_keys(self, tree: ast.Module, node_info) -> list[str]:
        if not node_info or not node_info.func_ref:
            return []
        for item in ast.iter_child_nodes(tree):
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name != node_info.func_ref:
                continue
            keys = []
            for node in ast.walk(item):
                if isinstance(node, ast.Return):
                    if node.value and isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant) and isinstance(
                                key.value, str
                            ):
                                keys.append(key.value)
            return keys
        return []

    def _extract_human_message_from_function(
        self, tree: ast.Module, node_info: Optional[_NodeInfo]
    ) -> str:
        """
        Extract HumanMessage content from a node function body.

        For literal strings, returns the exact content.
        For f-strings or variable references, tries to resolve the
        variable to its assigned value (often an f-string template).
        Returns empty string if only a simple variable name is found
        (runtime-only content), so caller can use the fallback.
        """
        if not node_info or not node_info.func_ref:
            return ""
        for item in ast.iter_child_nodes(tree):
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name != node_info.func_ref:
                continue

            # First, try to find the HumanMessage content
            hm_content_node = None
            for node in ast.walk(item):
                if isinstance(node, ast.Call):
                    name = ast_utils.get_call_name(node)
                    if name == "HumanMessage":
                        for kw in node.keywords:
                            if kw.arg == "content":
                                hm_content_node = kw.value
                                break
                        if hm_content_node is None and node.args:
                            hm_content_node = node.args[0]
                        break

            if hm_content_node is None:
                continue

            # If it's a literal string, return directly
            if isinstance(hm_content_node, ast.Constant) and isinstance(
                hm_content_node.value, str
            ):
                return hm_content_node.value

            # If it's an f-string (JoinedStr), unparse it
            if isinstance(hm_content_node, ast.JoinedStr):
                return ast.unparse(hm_content_node)

            # If it's a variable reference, try to resolve to its assignment
            if isinstance(hm_content_node, ast.Name):
                var_name = hm_content_node.id
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                        target = stmt.targets[0]
                        if isinstance(target, ast.Name) and target.id == var_name:
                            # Found the assignment — extract the value
                            if isinstance(stmt.value, ast.JoinedStr):
                                return ast.unparse(stmt.value)
                            if isinstance(stmt.value, ast.Constant) and isinstance(
                                stmt.value.value, str
                            ):
                                return stmt.value.value
                            # For complex expressions (f-strings with state refs),
                            # return the unparsed template
                            return ast.unparse(stmt.value)
                # Variable not found locally → it's runtime input, skip
                pass

            # If no HumanMessage found or failed to parse, look for dictionary return with 'messages' key
            for node in ast.walk(item):
                if (
                    isinstance(node, ast.Return)
                    and node.value
                    and isinstance(node.value, ast.Dict)
                ):
                    for key, val in zip(node.value.keys, node.value.values):
                        if isinstance(key, ast.Constant) and key.value == "messages":
                            if isinstance(val, ast.List):
                                for elt in val.elts:
                                    if (
                                        isinstance(elt, ast.Tuple)
                                        and len(elt.elts) >= 2
                                    ):
                                        first = elt.elts[0]
                                        second = elt.elts[1]
                                        if (
                                            isinstance(first, ast.Constant)
                                            and first.value == "user"
                                        ):
                                            if isinstance(
                                                second, ast.Constant
                                            ) and isinstance(second.value, str):
                                                return second.value
                                            elif isinstance(second, ast.JoinedStr):
                                                return ast.unparse(second)

            # Finally, check docstring
            doc = ast.get_docstring(item)
            if doc:
                return doc.strip()

        return ""

    # -----------------------------------------------------------
    # B4: Coordination Pattern Classification
    # -----------------------------------------------------------

    def _classify_coordination_pattern(
        self,
        nodes: dict[str, _NodeInfo],
        edges: list[tuple[str, str]],
        conditional_edges: list[_ConditionalEdge],
        entry_points: list[str],
    ) -> str:
        """
        Classify the graph topology into a coordination pattern.

        Sequential: linear chain A→B→C→END, no conditional edges
        ReActLoop: agent→tools_condition→ToolNode→agent loop detected
        Hierarchical: one node has conditional edges to ALL other agent nodes
        Custom: default fallback
        """
        agent_node_names = {n for n in nodes if n not in self._tool_node_names}

        # Check for Sequential: no conditional edges, linear chain
        if not conditional_edges and len(agent_node_names) > 1:
            return "Sequential"

        # Check for ReAct loop: a conditional edge from an agent node that
        # targets a ToolNode and loops back
        for ce in conditional_edges:
            targets = set(ce.mapping.values())
            has_tool_target = bool(targets & self._tool_node_names)
            has_end = "END" in targets or "__end__" in targets
            if has_tool_target and (has_end or targets & agent_node_names):
                return "ReActLoop"

        # Check for Hierarchical: one node routes to multiple agent nodes
        for ce in conditional_edges:
            targets = set(ce.mapping.values()) - {"END", "__end__"}
            agent_targets = targets & agent_node_names
            if len(agent_targets) >= 2:
                return "Hierarchical"

        # Default
        if conditional_edges:
            return "Custom"
        return "Sequential"

    # -----------------------------------------------------------
    # B5: Memory Detection from graph.compile()
    # -----------------------------------------------------------

    @staticmethod
    def _extract_compile_memory(tree: ast.Module) -> dict | None:
        """
        Detect checkpointer= and store= in graph.compile() calls.

        Returns dict with type and persistence info, or None.
        """
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "compile":
                continue

            result = {}
            for kw in node.keywords:
                if kw.arg == "checkpointer":
                    # MemorySaver, SqliteSaver, etc.
                    if isinstance(kw.value, ast.Call):
                        cls_name = ""
                        if isinstance(kw.value.func, ast.Name):
                            cls_name = kw.value.func.id
                        result["type"] = cls_name or "Checkpointer"
                        result["persistence"] = "ThreadScoped"
                        result["scope"] = "GroupShared"
                    elif isinstance(kw.value, ast.Name):
                        result["type"] = kw.value.id
                        result["persistence"] = "ThreadScoped"
                        result["scope"] = "GroupShared"
                elif kw.arg == "store":
                    if isinstance(kw.value, ast.Call):
                        cls_name = ""
                        if isinstance(kw.value.func, ast.Name):
                            cls_name = kw.value.func.id
                        result["type"] = cls_name or "Store"
                        result["persistence"] = "Persistent"
                        result["scope"] = "SystemGlobal"
                    elif isinstance(kw.value, ast.Name):
                        result["type"] = kw.value.id
                        result["persistence"] = "Persistent"
                        result["scope"] = "SystemGlobal"
            if result:
                return result
        return None

    # -----------------------------------------------------------
    # B6: interrupt() Detection
    # -----------------------------------------------------------

    def _detect_interrupts(
        self,
        tree: ast.Module,
        filepath: Path,
        nodes: dict[str, _NodeInfo],
    ) -> None:
        """Detect interrupt() calls in node functions and mark agents."""
        # Build func_name → node_name mapping
        func_to_node: dict[str, str] = {}
        for name, info in nodes.items():
            if info.func_ref:
                func_to_node[info.func_ref] = name

        for item in ast.iter_child_nodes(tree):
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name not in func_to_node:
                continue

            # Check if function body contains interrupt()
            for child in ast.walk(item):
                if isinstance(child, ast.Call):
                    call_name = ast_utils.get_call_name(child)
                    if call_name == "interrupt":
                        node_name = func_to_node[item.name]
                        agent_key = ast_utils.safe_key(node_name)
                        if agent_key in self.agents:
                            self.agents[agent_key].human_input = True
                            log.info(
                                "  [HITL] interrupt() detected in node '%s'", node_name
                            )

    # -----------------------------------------------------------
    # Module-Level LLM Detection
    # -----------------------------------------------------------

    def _extract_module_level_llms(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect LLM instantiations at module level.

        Patterns:
        - ``llm = ChatOpenAI(model="gpt-4o")``
        - ``llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")``
        - ``model_client = ChatOpenAI(model="gpt-4-turbo-preview")``
        """
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            call_name = ast_utils.get_call_name(node.value)
            if call_name in _LLM_CLASSES:
                model = self._extract_model_kwarg(node.value)
                if model:
                    self._module_llms[target.id] = model
                    log.info(
                        "  [LLM] Module-level %s = %s(model='%s') in %s",
                        target.id,
                        call_name,
                        model,
                        filepath.name,
                    )

    # -----------------------------------------------------------
    # Module-Level bind_tools Detection
    # -----------------------------------------------------------

    def _extract_bind_tools(self, tree: ast.Module, filepath: Path) -> None:
        """
        Detect ``.bind_tools([...])`` calls at module level.

        Patterns:
        - ``researcher_llm = llm.bind_tools([search_web, save_notes])``
        - ``model = ChatOpenAI(...).bind_tools(tools)``

        Populates ``self._bound_tools``: variable_name → set of tool names.
        """
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            if not isinstance(node.value.func, ast.Attribute):
                continue
            if node.value.func.attr != "bind_tools":
                continue

            # Extract tool names from the argument list
            tool_names: set[str] = set()
            if node.value.args:
                arg = node.value.args[0]
                if isinstance(arg, ast.List):
                    for elt in arg.elts:
                        if isinstance(elt, ast.Name):
                            tool_names.add(elt.id)
                elif isinstance(arg, ast.Name):
                    # Variable reference like bind_tools(tools) — resolve later
                    tool_names = self._resolve_tool_list_variable(tree, arg.id)

            if tool_names:
                self._bound_tools[target.id] = tool_names
                log.info(
                    "  [ToolBinding] %s = *.bind_tools(%s) in %s",
                    target.id,
                    tool_names,
                    filepath.name,
                )

    @staticmethod
    def _resolve_tool_list_variable(tree: ast.Module, var_name: str) -> set[str]:
        """Resolve a variable like ``tools = [add, subtract, multiply]``."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == var_name:
                    if isinstance(node.value, ast.List):
                        names = set()
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Name):
                                names.add(elt.id)
                        return names
        return set()

    # -----------------------------------------------------------
    # System Prompt Extraction from Functions
    # -----------------------------------------------------------

    @staticmethod
    def _extract_system_prompt(
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str:
        """
        Extract system prompt from a node function body.

        Detects these patterns:
        1. ``SystemMessage(content="...")``
        2. ``system_message = "..."`` or ``system_prompt = "..."``
           (string variable later used as system message)
        3. ``[{"role": "system", "content": "..."}]`` dict-style messages
        """
        # Pattern 1: SystemMessage(content="...")
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name == "SystemMessage":
                    # Check content= keyword
                    for kw in node.keywords:
                        if kw.arg == "content":
                            try:
                                return ast.literal_eval(kw.value)
                            except (ValueError, TypeError):
                                return ast.unparse(kw.value)
                    # Check first positional argument
                    if node.args:
                        try:
                            return ast.literal_eval(node.args[0])
                        except (ValueError, TypeError):
                            return ast.unparse(node.args[0])

        # Pattern 2: system_message = "..." or system_prompt = "..."
        prompt_var_names = {"system_message", "system_prompt", "sys_msg", "sys_prompt"}
        for node in ast.iter_child_nodes(func_node):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if (
                    isinstance(target, ast.Name)
                    and target.id.lower() in prompt_var_names
                ):
                    try:
                        return ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        return ast.unparse(node.value)

        # Pattern 3: [{"role": "system", "content": "..."}] in invoke calls
        for node in ast.walk(func_node):
            if isinstance(node, ast.Dict):
                role_val = None
                content_val = None
                for key, val in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "role":
                        if isinstance(val, ast.Constant) and val.value == "system":
                            role_val = "system"
                    if isinstance(key, ast.Constant) and key.value == "content":
                        content_val = val
                if role_val == "system" and content_val:
                    try:
                        return ast.literal_eval(content_val)
                    except (ValueError, TypeError):
                        return ast.unparse(content_val)

        return ""

    # -----------------------------------------------------------
    # Detect which model variable a function uses
    # -----------------------------------------------------------

    @staticmethod
    def _find_model_variable_in_function(
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> Optional[str]:
        """
        Find the model variable name used in a function body.

        Detects patterns like:
        - ``researcher_llm.invoke(...)``
        - ``model.invoke(...)``
        - ``model_with_tools.invoke(...)``
        """
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "invoke":
                    if isinstance(node.func.value, ast.Name):
                        return node.func.value.id
        return None

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
        - Falls back to module-level LLM if none found inside the function
        """
        # Build mapping: function_name → node_name
        # e.g. {"plan_step": "planner", "execute_step": "agent"}
        func_to_node: dict[str, str] = {}
        for name, info in nodes.items():
            if info.func_ref:
                # func_ref may be "plan_step" or "first_responder.respond"
                func_to_node[info.func_ref] = name

        for item in ast.iter_child_nodes(tree):
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name not in func_to_node:
                continue

            node_name = func_to_node[item.name]

            # This function is used as a graph node — check for LLM calls
            llm_model = self._find_llm_in_function(item)

            # Fallback: use module-level LLM if none found in function body
            if not llm_model and self._module_llms:
                llm_model = next(iter(self._module_llms.values()))

            # Extract system prompt from the function body
            system_prompt = self._extract_system_prompt(item)

            # Detect tool bindings: find which model variable the function uses
            # and check if that variable has bound tools
            agent_tools: list[str] = []
            model_var = self._find_model_variable_in_function(item)
            if model_var and model_var in self._bound_tools:
                agent_tools = sorted(self._bound_tools[model_var])
            elif model_var:
                # Check if this variable is a chained bind_tools call
                # e.g. model = ChatOpenAI(...).bind_tools(tools)
                # The variable itself may be in _bound_tools
                pass
            # Fallback: if there's only one bind_tools mapping, assign all tools
            if not agent_tools and len(self._bound_tools) == 1:
                only_key = next(iter(self._bound_tools))
                if model_var == only_key or model_var is None:
                    agent_tools = sorted(next(iter(self._bound_tools.values())))

            # Use the node name (not the function name) as the agent key
            # so it matches flow steps correctly
            agent_key = ast_utils.safe_key(node_name)
            agent = ExtractedAgent(
                agent_key=agent_key,
                role=node_name,
                goal=ast.get_docstring(item) or "",
                backstory=system_prompt,
                llm=llm_model,
                tools=agent_tools,
                source_file=str(filepath),
            )
            self.agents[agent_key] = agent
            log.info(
                "  [Agent] Node '%s' (func: %s, llm: %s, tools: %s, prompt: %s) from %s",
                node_name,
                item.name,
                llm_model or "unknown",
                agent_tools or "none",
                "yes" if system_prompt else "no",
                filepath.name,
            )

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
            if isinstance(node, ast.FunctionDef) and ast_utils.has_decorator(
                node, "tool"
            ):
                # Extract argument schema from function signature
                args_schema = self._extract_tool_args_schema(node)
                tool = ExtractedTool(
                    class_name=node.name,
                    name=node.name,
                    description=ast.get_docstring(node) or "",
                    args_schema_json=json.dumps(args_schema) if args_schema else "{}",
                    implementation_ref=f"{filepath.stem}.{node.name}",
                    source_file=str(filepath),
                )
                self.tools[node.name] = tool
                log.info(
                    "  [Tool] @tool function '%s' (args: %s) from %s",
                    node.name,
                    list(args_schema.get("properties", {}).keys()) or "none",
                    filepath.name,
                )

        # ToolNode([...]) calls — handles both Name refs and StructuredTool.from_function()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if ast_utils.get_call_name(node) == "ToolNode":
                    if node.args and isinstance(node.args[0], ast.List):
                        for elt in node.args[0].elts:
                            tool_name = None
                            if isinstance(elt, ast.Name):
                                tool_name = elt.id
                            elif isinstance(elt, ast.Call):
                                # StructuredTool.from_function(func, name="ToolName")
                                tool_name = self._extract_structured_tool_name(elt)
                            if tool_name and tool_name not in self.tools:
                                tool = ExtractedTool(
                                    class_name=tool_name,
                                    name=tool_name,
                                    description="",
                                    args_schema_json="{}",
                                    implementation_ref=f"{filepath.stem}.{tool_name}",
                                    source_file=str(filepath),
                                )
                                self.tools[tool_name] = tool
                                log.info(
                                    "  [Tool] ToolNode reference '%s' from %s",
                                    tool_name,
                                    filepath.name,
                                )

    # -----------------------------------------------------------
    # Pydantic Model Extraction
    # -----------------------------------------------------------

    def _extract_pydantic_models(self, tree: ast.Module, filepath: Path) -> None:
        """
        Scan for Pydantic BaseModel subclasses (including indirect inheritance).

        These capture structured output schemas (e.g. Plan, Reflection,
        AnswerQuestion) which are semantically important in LangGraph
        examples even though they are not explicit "tasks" or "agents".

        Uses two passes: first collects direct BaseModel children, then
        finds classes inheriting from already-known models.
        """
        known_bases = {"BaseModel"}

        # Two passes to handle inheritance chains (e.g. ReviseAnswer → AnswerQuestion → BaseModel)
        classes = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)]
        changed = True
        while changed:
            changed = False
            for node in classes:
                if node.name in self.pydantic_models:
                    continue
                if ast_utils.inherits_from(node, "TypedDict"):
                    continue
                if not any(ast_utils.inherits_from(node, b) for b in known_bases):
                    continue

                fields = ast_utils.extract_pydantic_fields(node)
                if not fields:
                    continue

                self.pydantic_models[node.name] = ExtractedPydanticModel(
                    class_name=node.name,
                    fields=fields,
                    source_file=str(filepath),
                )
                known_bases.add(node.name)
                changed = True
                log.info(
                    "  [PydanticModel] %s (%d fields) from %s",
                    node.name,
                    len(fields),
                    filepath.name,
                )

    # -----------------------------------------------------------
    # Router Target Inference
    # -----------------------------------------------------------

    @staticmethod
    def _infer_router_targets(
        sources: list[tuple[Path, str, ast.Module]],
        func_name: str,
    ) -> list[str]:
        """
        Infer routing targets from a router function's return statements
        and/or its ``Literal[...]`` return type annotation.

        This handles the common LangGraph pattern where
        ``add_conditional_edges("node", func)`` has no explicit mapping
        and the routing function returns string literals directly.
        """
        targets: set[str] = set()

        for _filepath, _source, tree in sources:
            for node in ast.iter_child_nodes(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name != func_name:
                    continue

                # 1. Try return type annotation: Literal["a", "b"]
                if node.returns and isinstance(node.returns, ast.Subscript):
                    if (
                        isinstance(node.returns.value, ast.Name)
                        and node.returns.value.id == "Literal"
                    ):
                        slic = node.returns.slice
                        if isinstance(slic, ast.Tuple):
                            for elt in slic.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    targets.add(elt.value)

                # 2. Collect string returns from the function body
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value:
                        if isinstance(child.value, ast.Constant) and isinstance(
                            child.value.str
                            if hasattr(child.value, "str")
                            else child.value.value,
                            str,
                        ):
                            targets.add(child.value.value)
                        elif isinstance(child.value, ast.Name):
                            # Handles "return END" → "END"
                            targets.add(child.value.id)

        return sorted(targets)

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
        sources: list[tuple[Path, str, ast.Module]] | None = None,
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
            # In LangGraph, a node can be both a start node AND have
            # conditional edges out of it. We prioritize "start" for the
            # decorator_type but still capture the routing logic.
            if name in entry_points:
                dec_type = "start"
            elif name in router_sources:
                dec_type = "router"
            else:
                dec_type = "regular"

            # Build dependencies (what this step listens to)
            incoming = [frm for frm, to in edges if to == name]
            # Also add conditional edges that target this node
            for ce in conditional_edges:
                for _val, target in ce.mapping.items():
                    if target == name and ce.source_node not in incoming:
                        incoming.append(ce.source_node)

            # Extract routing info if this node has conditional edges,
            # regardless of whether it's a start/regular/router node.
            return_values: list[str] = []
            function_body = ""
            edge_mapping: dict[str, str] = {}
            if name in router_sources:
                for ce in conditional_edges:
                    if ce.source_node == name:
                        return_values = list(ce.mapping.keys())
                        edge_mapping = dict(ce.mapping)
                        # Extract the actual router function body via ast.unparse
                        function_body = self._extract_router_function_body(
                            sources or [], ce.routing_func
                        )
                        if not function_body:
                            function_body = (
                                f"routing_function: {ce.routing_func or 'unknown'}"
                            )

            # dependencies: for CrewAI-style populator compatibility,
            # "regular" steps list what they listen TO (incoming edges).
            # "start" steps list outgoing targets.
            # "router" steps: targets are in return_values.
            if dec_type == "regular":
                dec_args = incoming
            elif dec_type == "start":
                # List targets so populator can find listeners
                dec_args = outgoing.get(name, [])
            else:
                dec_args = []

            step = ExtractedFlowStep(
                method_name=name,
                step_type=dec_type,
                dependencies=dec_args,
                calls_crew=None,
                return_values=return_values,
                function_body=function_body,
                edge_mapping=edge_mapping,
            )
            steps.append(step)

        return steps

    @staticmethod
    def _extract_router_function_body(
        sources: list[tuple[Path, str, ast.Module]],
        func_name: Optional[str],
    ) -> str:
        """
        Look up a routing function by name and return its body as Python code.

        Uses ``ast.unparse()`` to serialize the function body statements,
        preserving the actual routing logic for the semantic layer.
        """
        if not func_name:
            return ""
        for _filepath, _source, tree in sources:
            for node in ast.iter_child_nodes(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name != func_name:
                    continue
                # Unparse each statement in the function body (skip docstring)
                body_stmts = node.body
                if (
                    body_stmts
                    and isinstance(body_stmts[0], ast.Expr)
                    and isinstance(body_stmts[0].value, ast.Constant)
                    and isinstance(body_stmts[0].value.value, str)
                ):
                    body_stmts = body_stmts[1:]  # skip docstring
                if body_stmts:
                    return "\n".join(ast.unparse(stmt) for stmt in body_stmts)
        return ""

    # -----------------------------------------------------------
    # AST Helper Methods
    # -----------------------------------------------------------

    @staticmethod
    def _extract_first_string_arg(node: ast.Call) -> Optional[str]:
        """Extract the first positional argument if it's a string constant."""
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return node.args[0].value
        return None

    @staticmethod
    def _extract_second_arg_name(node: ast.Call) -> Optional[str]:
        """Extract the second positional argument if it's a Name or Attribute."""
        if len(node.args) < 2:
            return None
        arg = node.args[1]
        if isinstance(arg, ast.Name):
            return arg.id
        # Handle attribute access: e.g., first_responder.respond → "first_responder.respond"
        if isinstance(arg, ast.Attribute):
            parts = []
            current = arg
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts)) if parts else None
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
    def _extract_mapping_arg(node: ast.Call) -> dict[str, str]:
        """
        Extract the routing mapping from add_conditional_edges().

        Handles three forms:
        1. Dict literal:  {"val": "target", ...}  → {"val": "target"}
        2. List literal:  ["target1", END]         → {"target1": "target1", "END": "END"}
        3. Missing:       (only source + func)     → {}

        The list form is common in LangGraph where the routing function
        returns one of the list elements directly (identity mapping).
        """
        if len(node.args) < 3:
            return {}
        arg = node.args[2]

        # Dict literal: {"key": "target", ...}
        if isinstance(arg, ast.Dict):
            result = {}
            for key, val in zip(arg.keys, arg.values):
                k = ast_utils.ast_to_string(key)
                v = ast_utils.ast_to_string(val)
                if k and v:
                    result[k] = v
            return result

        # List literal: ["target1", "target2"] → identity mapping
        if isinstance(arg, ast.List):
            result = {}
            for elt in arg.elts:
                v = ast_utils.ast_to_string(elt)
                if v:
                    result[v] = v
            return result

        return {}

    @staticmethod
    def _extract_structured_tool_name(call: ast.Call) -> Optional[str]:
        """
        Extract the tool name from StructuredTool.from_function(func, name="X").

        Returns the ``name`` keyword if present, otherwise the first
        positional argument's name (the function reference).
        """
        # Check it's a from_function call
        if isinstance(call.func, ast.Attribute) and call.func.attr == "from_function":
            # Try name= keyword first
            for kw in call.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
            # Fallback: first positional arg (the function)
            if call.args and isinstance(call.args[0], ast.Name):
                return call.args[0].id
        return None

    @staticmethod
    def _extract_model_kwarg(call: ast.Call) -> Optional[str]:
        """Extract the model= keyword argument from an LLM constructor call."""
        for kw in call.keywords:
            if kw.arg == "model" and isinstance(kw.value, ast.Constant):
                return str(kw.value.value)
        return None

    @staticmethod
    def _extract_tool_args_schema(func_node: ast.FunctionDef) -> dict:
        """
        Build a JSON Schema dict from a @tool function's parameters.

        Extracts parameter names, type annotations, and builds a schema
        like ``{"type": "object", "properties": {"a": {"type": "integer"}, ...}}``.
        """
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
                elif isinstance(arg.annotation, ast.Constant):
                    prop["type"] = str(arg.annotation.value)
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

    @staticmethod
    def _extract_typeddict_fields(tree: ast.Module, class_name: str) -> dict[str, str]:
        """
        Extract field names and type annotations from a TypedDict class.

        Returns a dict of ``{field_name: type_string}``.
        """
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name != class_name:
                continue
            fields: dict[str, str] = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    if isinstance(item.annotation, ast.Name):
                        fields[item.target.id] = item.annotation.id
                    elif isinstance(item.annotation, ast.Subscript):
                        # Handle Annotated[list, add_messages] etc.
                        fields[item.target.id] = ast.unparse(item.annotation)
                    else:
                        fields[item.target.id] = ast.unparse(item.annotation)
            return fields
        return {}

    @staticmethod
    def _find_llm_in_function(
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> Optional[str]:
        """
        Search a function body for LLM instantiation patterns like:
        - ChatOpenAI(model="gpt-4")
        - ChatAnthropic(model="claude-3")
        """
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in _LLM_CLASSES:
                    for kw in node.keywords:
                        if kw.arg == "model" and isinstance(kw.value, ast.Constant):
                            return str(kw.value.value)
        return None


# -----------------------------------------------------------
# Module-level helpers
# -----------------------------------------------------------


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

    def __init__(
        self, source_node: str, routing_func: Optional[str], mapping: dict[str, str]
    ):
        self.source_node = source_node
        self.routing_func = routing_func
        self.mapping = mapping
