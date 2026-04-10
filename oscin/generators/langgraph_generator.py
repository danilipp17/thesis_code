"""
langgraph_generator.py
======================
LangGraph code generator for the OSCIN reverse pipeline.

Generates a single ``main.py`` with ``StateGraph`` construction,
node definitions, edge/conditional-edge wiring, and a ``compile()``
call.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import logging
from pathlib import Path

from oscin.generators.base_generator import BaseCodeGenerator

log = logging.getLogger("oscin")


class LangGraphGenerator(BaseCodeGenerator):
    """
    Generates a LangGraph project from the intermediate representations.

    Output structure:
    - ``main.py`` — StateGraph with nodes, edges, and compilation
    - ``tools.py`` — @tool function definitions (if any)
    """

    @staticmethod
    def framework_name() -> str:
        return "LangGraph"

    def generate(self) -> list[Path]:
        log.info("")
        log.info("=" * 60)
        log.info("GENERATING LANGGRAPH SOURCE CODE")
        log.info("Output directory: %s", self.output_dir)
        log.info("=" * 60)

        if self.reader.tools:
            self._generate_tools_file()

        self._generate_main()

        log.info("")
        log.info("=" * 60)
        log.info("LANGGRAPH GENERATION COMPLETE — %d files written",
                 len(self._created_files))
        log.info("=" * 60)

        return self._created_files

    # -----------------------------------------------------------
    # Tool Generation
    # -----------------------------------------------------------

    def _generate_tools_file(self) -> None:
        """Generate a tools.py with @tool-decorated function skeletons."""
        lines = [
            '"""',
            "Auto-generated LangGraph tool definitions.",
            '"""',
            "",
            "from langchain_core.tools import tool",
            "",
        ]

        for key, tool in self.reader.tools.items():
            func_name = self._to_snake(key)
            lines.extend([
                "",
                "@tool",
                f'def {func_name}(**kwargs) -> str:',
                f'    """',
                f'    {tool.name}',
                f'    {tool.description}',
                f'    """',
                f'    raise NotImplementedError("TODO: implement {tool.name}")',
                "",
            ])

        self._write_file("tools.py", "\n".join(lines))

    # -----------------------------------------------------------
    # Main Generation
    # -----------------------------------------------------------

    def _generate_main(self) -> None:
        """Generate main.py with StateGraph construction."""
        lines = [
            '"""',
            f"Auto-generated LangGraph application: {self.reader.system_name}",
            '"""',
            "",
            "from typing import Annotated, TypedDict",
            "",
            "from langgraph.graph import END, START, StateGraph",
            "from langgraph.graph.message import add_messages",
            "from langchain_openai import ChatOpenAI",
            "",
        ]

        # Tool imports
        if self.reader.tools:
            tool_funcs = ", ".join(self._to_snake(k) for k in self.reader.tools)
            lines.extend([
                f"from tools import {tool_funcs}",
                "from langgraph.prebuilt import ToolNode",
                "",
            ])

        # State definition
        lines.extend([
            "",
            "class State(TypedDict):",
            '    """Graph state."""',
            '    messages: Annotated[list, add_messages]',
            "",
        ])

        # LLM setup
        llm_models = set()
        for agent in self.reader.agents.values():
            if agent.llm:
                llm_models.add(agent.llm)
        model = next(iter(llm_models), "gpt-4o")

        lines.extend([
            f'model = ChatOpenAI(model="{model}")',
            "",
        ])

        # Tool binding
        if self.reader.tools:
            tool_list = ", ".join(self._to_snake(k) for k in self.reader.tools)
            lines.extend([
                f"tools = [{tool_list}]",
                "model_with_tools = model.bind_tools(tools)",
                "tool_node = ToolNode(tools)",
                "",
            ])

        # Node functions
        # If we have a flow with steps, use those
        if self.reader.flow:
            for step in self.reader.flow.steps:
                func_name = self._to_snake(step.method_name)
                if step.decorator_type == "router":
                    lines.extend(self._render_router_function(func_name, step))
                else:
                    lines.extend(self._render_node_function(func_name, step))
        else:
            # Fallback: create a node per agent
            for key, agent in self.reader.agents.items():
                func_name = self._to_snake(key)
                lines.extend([
                    "",
                    f"def {func_name}(state: State) -> State:",
                    f'    """',
                    f'    {agent.role}',
                    f'    {agent.goal}',
                    f'    """',
                    f'    messages = state["messages"]',
                ])
                if self.reader.tools:
                    lines.append(f"    response = model_with_tools.invoke(messages)")
                else:
                    lines.append(f"    response = model.invoke(messages)")
                lines.extend([
                    f'    return {{"messages": [response]}}',
                    "",
                ])

        # Graph construction
        lines.extend([
            "",
            "# Build the graph",
            "graph = StateGraph(State)",
            "",
        ])

        if self.reader.flow:
            # Add nodes
            for step in self.reader.flow.steps:
                if step.decorator_type != "router":
                    func_name = self._to_snake(step.method_name)
                    lines.append(f'graph.add_node("{step.method_name}", {func_name})')

            # Add tool node if any
            if self.reader.tools:
                lines.append('graph.add_node("tools", tool_node)')

            lines.append("")

            # Add edges based on flow structure
            for step in self.reader.flow.steps:
                if step.decorator_type == "start":
                    lines.append(f'graph.add_edge(START, "{step.method_name}")')

                elif step.decorator_type == "router":
                    # Conditional edges
                    func_name = self._to_snake(step.method_name)
                    mapping_entries = []
                    for rv in step.return_values:
                        # Check if return value is a step name or a label
                        target = rv
                        mapping_entries.append(f'        "{rv}": "{target}"')
                    if mapping_entries:
                        # Find the source node this router follows
                        # Router in CrewAI is after a @start, so find that predecessor
                        source = step.decorator_args[0] if step.decorator_args else step.method_name
                        lines.append(
                            f'graph.add_conditional_edges(\n'
                            f'    "{source}",\n'
                            f'    {func_name},\n'
                            f'    {{\n'
                            + ",\n".join(mapping_entries) + "\n"
                            f'    }},\n'
                            f')'
                        )

            # End edges: steps with no outgoing edges get → END
            # Detect end steps from the flow
            has_outgoing = set()
            for step in self.reader.flow.steps:
                if step.decorator_type == "start":
                    has_outgoing.add(step.method_name)
                elif step.decorator_type == "router":
                    # Source of router has outgoing
                    if step.decorator_args:
                        has_outgoing.add(step.decorator_args[0])

            for step in self.reader.flow.steps:
                if step.decorator_type == "listen" and step.method_name not in has_outgoing:
                    lines.append(f'graph.add_edge("{step.method_name}", END)')

        else:
            # No flow — chain agents sequentially
            agent_keys = list(self.reader.agents.keys())
            for i, key in enumerate(agent_keys):
                func_name = self._to_snake(key)
                lines.append(f'graph.add_node("{key}", {func_name})')

            if self.reader.tools:
                lines.append('graph.add_node("tools", tool_node)')

            lines.append("")

            if agent_keys:
                lines.append(f'graph.add_edge(START, "{agent_keys[0]}")')
                for i in range(len(agent_keys) - 1):
                    lines.append(f'graph.add_edge("{agent_keys[i]}", "{agent_keys[i+1]}")')
                lines.append(f'graph.add_edge("{agent_keys[-1]}", END)')

        # Compile and run
        lines.extend([
            "",
            "# Compile the graph",
            "app = graph.compile()",
            "",
            "",
            'if __name__ == "__main__":',
            '    result = app.invoke({"messages": ["Start the task."]})',
            '    print(result["messages"][-1].content)',
            "",
        ])

        self._write_file("main.py", "\n".join(lines))

    # -----------------------------------------------------------
    # Node Function Renderers
    # -----------------------------------------------------------

    def _render_node_function(self, func_name: str, step) -> list[str]:
        """Render a standard node function."""
        lines = [
            "",
            f"def {func_name}(state: State) -> State:",
            f'    """Node: {step.method_name}"""',
            f'    messages = state["messages"]',
        ]
        if self.reader.tools:
            lines.append("    response = model_with_tools.invoke(messages)")
        else:
            lines.append("    response = model.invoke(messages)")
        lines.extend([
            '    return {"messages": [response]}',
            "",
        ])
        return lines

    def _render_router_function(self, func_name: str, step) -> list[str]:
        """Render a routing function for conditional edges."""
        lines = [
            "",
            f"def {func_name}(state: State) -> str:",
            f'    """Router: {step.method_name}"""',
        ]
        if step.return_values:
            for i, rv in enumerate(step.return_values):
                if i == 0:
                    lines.append(f'    # if condition:')
                    lines.append(f'    #     return "{rv}"')
                else:
                    lines.append(f'    # return "{rv}"')
            lines.append(f'    return "{step.return_values[0]}"  # TODO: implement routing logic')
        else:
            lines.append('    return "end"  # TODO: implement routing logic')
        lines.append("")
        return lines
