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
import textwrap
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
        log.info(
            "LANGGRAPH GENERATION COMPLETE — %d files written", len(self._created_files)
        )
        log.info("=" * 60)

        return self._created_files

    # -----------------------------------------------------------
    # Tool Generation
    # -----------------------------------------------------------

    def _generate_tools_file(self) -> None:
        """Generate a tools.py with @tool-decorated function skeletons using Jinja2."""
        template = self.jinja_env.get_template("langgraph_tools.py.j2")
        tools_data = []

        for key, tool in self.reader.tools.items():
            func_name = self._to_snake(key)
            params = self._build_tool_params(tool)
            tools_data.append(
                {
                    "func_name": func_name,
                    "params": params,
                    "name": tool.name,
                    "description": tool.description,
                }
            )

        content = template.render(tools=tools_data)
        self._write_file("tools.py", content)

    def _build_tool_params(self, tool) -> str:
        """Build parameter string from tool's args_schema_json."""
        import json

        try:
            schema = json.loads(tool.args_schema_json)
        except (json.JSONDecodeError, TypeError):
            return "**kwargs"

        if not schema or "properties" not in schema:
            return "**kwargs"

        _type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }

        params = []
        for name, prop in schema["properties"].items():
            py_type = _type_map.get(prop.get("type", "string"), "str")
            params.append(f"{name}: {py_type}")

        return ", ".join(params) if params else "**kwargs"

    # -----------------------------------------------------------
    # Main Generation
    # -----------------------------------------------------------

    def _generate_main(self) -> None:
        """Generate main.py with StateGraph construction."""
        # Determine if any agent has a system prompt
        has_system_prompts = any(a.backstory for a in self.reader.agents.values())

        lines = [
            '"""',
            f"Auto-generated LangGraph application: {self.reader.system_name}",
            '"""',
            "",
            "import dotenv",
            "from typing import Annotated, TypedDict",
            "",
            "from langgraph.graph import END, START, StateGraph",
            "",
            "dotenv.load_dotenv()",
            "from langgraph.graph.message import add_messages",
            "from langchain_openai import ChatOpenAI",
        "from langchain_core.messages import SystemMessage, HumanMessage",
        ]

        if has_system_prompts:
            lines.append("from langchain_core.messages import SystemMessage, HumanMessage")

        lines.append("")

        # Tool imports
        if self.reader.tools:
            tool_funcs = ", ".join(self._to_snake(k) for k in self.reader.tools)
            lines.extend(
                [
                    f"from tools import {tool_funcs}",
                    "from langgraph.prebuilt import ToolNode",
                    "",
                ]
            )

        # State definition — use actual fields if available from semantic layer
        lines.extend(self._generate_state_class())

        # LLM setup
        llm_models = set()
        for agent in self.reader.agents.values():
            if agent.llm:
                llm_models.add(agent.llm)
        model = next(iter(llm_models), "gpt-4o")

        lines.extend(
            [
                f'model = ChatOpenAI(model="{model}")',
                "",
            ]
        )

        # Per-agent tool binding
        # Build a mapping of which agents have tools
        agents_with_tools = {k: a for k, a in self.reader.agents.items() if a.tools}
        agents_without_tools = {
            k: a for k, a in self.reader.agents.items() if not a.tools
        }

        if self.reader.tools:
            tool_list = ", ".join(self._to_snake(k) for k in self.reader.tools)
            lines.extend(
                [
                    f"tools = [{tool_list}]",
                    "tool_node = ToolNode(tools)",
                    "",
                ]
            )

            if agents_with_tools and agents_without_tools:
                # Some agents have tools, some don't — generate per-agent bindings
                for key, agent in agents_with_tools.items():
                    agent_tool_list = ", ".join(self._to_snake(t) for t in agent.tools)
                    var_name = self._to_snake(key) + "_model"
                    lines.append(f"{var_name} = model.bind_tools([{agent_tool_list}])")
                lines.append("")
            elif agents_with_tools:
                # All agents have tools
                lines.extend(
                    [
                        "model_with_tools = model.bind_tools(tools)",
                        "",
                    ]
                )

        # Node functions
        if self.reader.flow:
            for step in self.reader.flow.steps:
                func_name = self._to_snake(step.method_name)
                # Check if this step has routing logic (router or start+conditional)
                has_routing = (
                    step.return_values or step.edge_mapping
                ) and step.function_body
                if has_routing:
                    # It's a node with conditional routing — generate node func + router
                    lines.extend(self._render_node_function(func_name, step))
                    router_name = f"route_{func_name}"
                    lines.extend(self._render_router_function(router_name, step))
                elif step.step_type == "router":
                    lines.extend(self._render_router_function(func_name, step))
                else:
                    lines.extend(self._render_node_function(func_name, step))
        else:
            # Fallback: create a node per agent
            for key, agent in self.reader.agents.items():
                func_name = self._to_snake(key)
                lines.extend(self._render_agent_node_function(func_name, agent))

        # Graph construction
        lines.extend(
            [
                "",
                "# Build the graph",
                "graph = StateGraph(State)",
                "",
            ]
        )

        if self.reader.flow:
            self._generate_flow_graph(lines)
        else:
            self._generate_sequential_graph(lines)

        # Compile and run
        lines.extend(
            [
                "",
                "# Compile the graph",
                "app = graph.compile()",
                "",
                "",
                'if __name__ == "__main__":',
                '    result = app.invoke({"messages": ["Start the task."]})',
                '    print(result["messages"][-1].content)',
                "",
            ]
        )

        self._write_file("main.py", "\n".join(lines))

    # -----------------------------------------------------------
    # State Class Generation
    # -----------------------------------------------------------

    def _generate_state_class(self) -> list[str]:
        """Generate the State TypedDict from semantic layer state fields."""
        lines = [
            "",
            "class State(TypedDict):",
            '    """Graph state."""',
            "    messages: Annotated[list, add_messages]",
        ]

        state_fields = {}
        if self.reader.flow and hasattr(self.reader.flow, "state_fields"):
            state_fields = self.reader.flow.state_fields or {}

        for field_name, field_type in state_fields.items():
            if field_name == "messages":
                continue  # Handled above
            # Handle standard python types from JSON types
            py_type = "str"
            if field_type == "integer":
                py_type = "int"
            elif field_type == "boolean":
                py_type = "bool"
            elif field_type == "number":
                py_type = "float"
            elif field_type == "array":
                py_type = "list"
            elif field_type == "object":
                py_type = "dict"
            elif field_type in ("str", "int", "float", "bool", "list", "dict"):
                py_type = field_type

            lines.append(f"    {field_name}: {py_type}")

        lines.append("")
        return lines

    # -----------------------------------------------------------
    # Node Function Renderers
    # -----------------------------------------------------------

    def _render_node_function(self, func_name: str, step) -> list[str]:
        """Render a standard node function with system prompt if available."""

        # Subgraph invocation
        if step.calls_crew:
            team = self.reader.teams.get(step.calls_crew)
            team_name = team.team_class_name if team else "SubGraph"
            return [
                "",
                f"def {func_name}(state: State) -> dict:",
                f'    """Subgraph node: {step.method_name}"""',
                f"    # TODO: Initialize and invoke the {team_name} compiled subgraph here",
                f'    return {{"messages": []}}',
                "",
            ]

        # Find the corresponding agent for this step
        agent = self._find_agent_for_step(step)

        lines = [
            "",
            f"def {func_name}(state: State) -> dict:",
            f'    """Node: {step.method_name}"""',
        ]

        messages_init = []
        if agent and agent.backstory:
            escaped = agent.backstory.replace('"""', '\"\"\"')
            messages_init.extend([
                f"    system_prompt = SystemMessage(content=",
                f'        """{escaped}"""',
                f"    )"
            ])
            
        # Get dynamic task prompt
        task = self._find_task_for_agent(agent)
        task_prompt_code = None
        if task and task.description and "Perform " not in task.description:
            import re
            # Extract variables like {topic} from the task description
            vars_in_prompt = re.findall(r'\{([a-zA-Z0-9_]+)\}', task.description)
            for v in set(vars_in_prompt):
                messages_init.append(f"    {v} = state.get('{v}', '')")
            
            # Now the prompt
            if task.description.startswith("f'") or task.description.startswith('f"'):
                desc_val = task.description
            else:
                desc_val = f'f"""{task.description}"""'
            messages_init.append(f"    task_prompt = {desc_val}")
            task_prompt_code = "HumanMessage(content=task_prompt)"

        if agent and agent.backstory and task_prompt_code:
            messages_init.append(f'    messages = [system_prompt] + state.get("messages", []) + [{task_prompt_code}]')
        elif agent and agent.backstory:
            messages_init.append(f'    messages = [system_prompt] + state.get("messages", [])')
        elif task_prompt_code:
            messages_init.append(f'    messages = state.get("messages", []) + [{task_prompt_code}]')
        else:
            messages_init.append(f'    messages = state.get("messages", [])')
            
        lines.extend(messages_init)

        # Find associated task to get expected output
        task = self._find_task_for_agent(agent)
        return_dict = '{"messages": [response]}'
        if task and task.expected_output:
            keys = [k.strip() for k in task.expected_output.split(',')]
            if keys:
                ret_str = ", ".join([f'"{k}": response.content' for k in keys])
                return_dict = f'{{{ret_str}}}'

        # Use appropriate model (with or without tools)
        model_var = self._get_model_var_for_agent(agent)
        lines.extend(
            [
                f"    response = {model_var}.invoke(messages)",
                f"    return {return_dict}",
                "",
            ]
        )
        return lines

    def _render_agent_node_function(self, func_name: str, agent) -> list[str]:
        """Render a node function for a fallback agent (no flow)."""
        lines = [
            "",
            f"def {func_name}(state: State) -> dict:",
            f'    """{agent.role}: {agent.goal}"""',
        ]

        if agent.backstory:
            escaped = agent.backstory.replace('"""', '\\"\\"\\"')
            lines.extend(
                [
                    f"    system_prompt = SystemMessage, HumanMessage(content=",
                    f'        """{escaped}"""',
                    f"    )",
                    f'    messages = [system_prompt] + state["messages"]',
                ]
            )
        else:
            lines.append(f'    messages = state["messages"]')

        task = self._find_task_for_agent(agent)
        return_dict = '{"messages": [response]}'
        if task and task.expected_output:
            keys = [k.strip() for k in task.expected_output.split(',')]
            if keys:
                ret_str = ", ".join([f'"{k}": response.content' for k in keys])
                return_dict = f'{{{ret_str}}}'

        model_var = self._get_model_var_for_agent(agent)
        lines.extend(
            [
                f"    response = {model_var}.invoke(messages)",
                f"    return {return_dict}",
                "",
            ]
        )
        return lines

    def _render_router_function(self, func_name: str, step) -> list[str]:
        """Render a routing function for conditional edges."""
        lines = [
            "",
            f"def {func_name}(state: State) -> str:",
            f'    """Router: {step.method_name}"""',
        ]

        # If we have actual routing logic from extraction, emit it
        if step.function_body and not step.function_body.startswith(
            "routing_function:"
        ):
            # Indent the extracted function body
            body = textwrap.dedent(step.function_body).strip("\n")
            for body_line in body.split("\n"):
                if body_line.strip():
                    lines.append(f"    {body_line}")
                else:
                    lines.append("")
            lines.append("")
        elif step.return_values:
            # Fallback: generate stub with return value hints
            for i, rv in enumerate(step.return_values):
                if i == 0:
                    lines.append(f"    # if condition:")
                    lines.append(f'    #     return "{rv}"')
                else:
                    lines.append(f'    # return "{rv}"')
            lines.append(
                f'    return "{step.return_values[0]}"  # TODO: implement routing logic'
            )
            lines.append("")
        else:
            lines.append('    return "end"  # TODO: implement routing logic')
            lines.append("")

        return lines

    # -----------------------------------------------------------
    # Graph Construction
    # -----------------------------------------------------------

    def _generate_flow_graph(self, lines: list[str]) -> None:
        """Generate graph nodes and edges from flow structure."""
        # Add nodes
        for step in self.reader.flow.steps:
            func_name = self._to_snake(step.method_name)
            lines.append(f'graph.add_node("{step.method_name}", {func_name})')

        # Add tool node if any tools exist
        if self.reader.tools:
            lines.append('graph.add_node("tools", tool_node)')

        lines.append("")

        # Add edges based on flow structure
        for step in self.reader.flow.steps:
            if step.step_type == "start":
                lines.append(f'graph.add_edge(START, "{step.method_name}")')

                # If start step has routing (conditional edges)
                if (step.return_values or step.edge_mapping) and step.function_body:
                    router_name = f"route_{self._to_snake(step.method_name)}"
                    mapping_entries = self._build_mapping_entries(step)
                    if mapping_entries:
                        lines.append(
                            f"graph.add_conditional_edges(\n"
                            f'    "{step.method_name}",\n'
                            f"    {router_name},\n"
                            f"    {{\n" + ",\n".join(mapping_entries) + "\n"
                            f"    }},\n"
                            f")"
                        )
            elif step.step_type == "conditional":
                func_name = self._to_snake(step.method_name)
                source = step.dependencies[0] if step.dependencies else step.method_name

                # Check if it has an explicit routing body, if so it generated a route_func
                if step.function_body:
                    router_name = f"route_{func_name}"
                else:
                    router_name = func_name

                mapping_entries = self._build_mapping_entries(step)
                if mapping_entries:
                    lines.append(
                        f"graph.add_conditional_edges(\n"
                        f'    "{source}",\n'
                        f"    {router_name},\n"
                        f"    {{\n" + ",\n".join(mapping_entries) + "\n"
                        f"    }},\n"
                        f")"
                    )
            elif step.step_type == "regular":
                for dep in step.dependencies:
                    lines.append(f'graph.add_edge("{dep}", "{step.method_name}")')

        # End edges: listen steps with no outgoing edges
        has_outgoing = set()
        for step in self.reader.flow.steps:
            if step.return_values or step.edge_mapping:
                has_outgoing.add(step.method_name)
            if (
                step.step_type == "start"
                and not step.return_values
                and not step.edge_mapping
            ):
                has_outgoing.add(step.method_name)

        for step in self.reader.flow.steps:
            if step.return_values or step.edge_mapping:
                has_outgoing.add(step.method_name)
            if (
                step.step_type == "start"
                and not step.return_values
                and not step.edge_mapping
            ):
                has_outgoing.add(step.method_name)

        for step in self.reader.flow.steps:
            if step.step_type == "listen" and step.method_name not in has_outgoing:
                lines.append(f'graph.add_edge("{step.method_name}", END)')

        # Add tool-agent loop edges if tools exist
        if self.reader.tools:
            # Find steps that use agents with tools
            for step in self.reader.flow.steps:
                agent = self._find_agent_for_step(step)
                if agent and agent.tools:
                    lines.append(f'graph.add_edge("tools", "{step.method_name}")')

    def _generate_sequential_graph(self, lines: list[str]) -> None:
        """Generate a sequential graph when no flow is defined."""
        agent_keys = list(self.reader.agents.keys())
        for key in agent_keys:
            func_name = self._to_snake(key)
            lines.append(f'graph.add_node("{key}", {func_name})')

        if self.reader.tools:
            lines.append('graph.add_node("tools", tool_node)')
            for key in agent_keys:
                agent = self.reader.agents.get(key)
                if agent and agent.tools:
                    lines.append(f'graph.add_edge("tools", "{key}")')

        lines.append("")

        if agent_keys:
            lines.append(f'graph.add_edge(START, "{agent_keys[0]}")')
            for i in range(len(agent_keys) - 1):
                lines.append(
                    f'graph.add_edge("{agent_keys[i]}", "{agent_keys[i + 1]}")'
                )
            lines.append(f'graph.add_edge("{agent_keys[-1]}", END)')

    # -----------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------

    @staticmethod
    def _build_mapping_entries(step) -> list[str]:
        """Build conditional edge mapping entries from step's edge_mapping or return_values."""
        entries = []
        if step.edge_mapping:
            # Use the actual mapping (label → target)
            for label, target in step.edge_mapping.items():
                # Handle END target
                if target == "END":
                    entries.append(f'        "{label}": END')
                else:
                    entries.append(f'        "{label}": "{target}"')
        else:
            # Fallback: identity mapping (return value = target node)
            for rv in step.return_values:
                entries.append(f'        "{rv}": "{rv}"')
        return entries

    def _find_agent_for_step(self, step) -> object | None:
        """Find the agent associated with a flow step."""
        step_key = self._to_snake(step.method_name).replace("-", "_")
        # Try direct match
        if step_key in self.reader.agents:
            return self.reader.agents[step_key]
        # Try step.method_name directly
        if step.method_name in self.reader.agents:
            return self.reader.agents[step.method_name]
        return None


    def _find_task_for_agent(self, agent) -> object | None:
        if not agent: return None
        for task in self.reader.tasks.values():
            if task.agent_key == agent.agent_key:
                return task
        return None

    def _get_model_var_for_agent(self, agent) -> str:
        """Get the appropriate model variable for an agent."""
        if not agent or not agent.tools:
            return "model"

        # Check if all agents have tools (use model_with_tools)
        agents_with_tools = {k for k, a in self.reader.agents.items() if a.tools}
        agents_without_tools = {k for k, a in self.reader.agents.items() if not a.tools}

        if agents_with_tools and agents_without_tools:
            # Per-agent tool binding
            return self._to_snake(agent.agent_key) + "_model"
        elif agents_with_tools:
            return "model_with_tools"
        return "model"
