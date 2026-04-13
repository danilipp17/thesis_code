"""
autogen_generator.py
====================
AutoGen v0.4 code generator for the OSCIN reverse pipeline.

Generates a single ``main.py`` with AutoGen v0.4 agent instantiations,
team setup (RoundRobinGroupChat), and async execution.

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from oscin.generators.base_generator import BaseCodeGenerator

log = logging.getLogger("oscin")


class AutoGenGenerator(BaseCodeGenerator):
    """
    Generates an AutoGen v0.4 project from the intermediate representations.

    Output structure:
    - ``main.py`` — agent instantiations, team, and async execution
    - ``tools.py`` — tool function definitions (if any)
    """

    @staticmethod
    def framework_name() -> str:
        return "AutoGen"

    def generate(self) -> list[Path]:
        log.info("")
        log.info("=" * 60)
        log.info("GENERATING AUTOGEN SOURCE CODE")
        log.info("Output directory: %s", self.output_dir)
        log.info("=" * 60)

        if self.reader.tools:
            self._generate_tools_file()

        self._generate_main()

        log.info("")
        log.info("=" * 60)
        log.info(
            "AUTOGEN GENERATION COMPLETE — %d files written", len(self._created_files)
        )
        log.info("=" * 60)

        return self._created_files

    # -----------------------------------------------------------
    # Tool Generation
    # -----------------------------------------------------------

    def _generate_tools_file(self) -> None:
        """Generate a tools.py with function skeletons."""
        lines = [
            '"""',
            "Auto-generated AutoGen tool definitions.",
            '"""',
            "",
        ]

        for key, tool in self.reader.tools.items():
            func_name = self._to_snake(key)
            # Generate typed parameters from args_schema
            params = self._build_tool_params(tool)
            desc = tool.description.replace('"""', '\\"\\"\\"')
            lines.extend(
                [
                    "",
                    f"def {func_name}({params}) -> str:",
                    f'    """',
                    f"    {tool.name}",
                ]
            )
            if desc:
                for desc_line in desc.split("\n"):
                    lines.append(f"    {desc_line}")
            if tool.implementation_ref:
                lines.append(f"")
                lines.append(f"    Implementation reference: {tool.implementation_ref}")
            lines.extend(
                [
                    f'    """',
                    f'    raise NotImplementedError("TODO: implement {tool.name}")',
                    "",
                ]
            )

        self._write_file("tools.py", "\n".join(lines))

    def _build_tool_params(self, tool) -> str:
        """Build typed parameter string from tool's args_schema_json."""
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
        """Generate the main.py with AutoGen v0.4 agent setup using Jinja2."""
        # LLM client — collect unique models
        llm_models = set()
        for agent in self.reader.agents.values():
            if agent.llm:
                llm_models.add(agent.llm)
        model = next(iter(llm_models), "gpt-4o")

        tools_list = []
        tools_config = []
        if self.reader.tools:
            tools_list = [self._to_snake(k) for k in self.reader.tools]
            for key, tool in self.reader.tools.items():
                func_name = self._to_snake(key)
                var_name = f"{func_name}_tool"
                desc = tool.description.replace('"', '\\"').replace("\n", " ")
                tools_config.append(
                    {
                        "var_name": var_name,
                        "func_name": func_name,
                        "desc": desc,
                    }
                )

        agents_data = []
        agent_vars: dict[str, str] = {}
        for key, agent in self.reader.agents.items():
            var_name = self._to_snake(key)
            agent_vars[key] = var_name

            system_parts = []
            if agent.goal:
                system_parts.append(agent.goal)
            if agent.backstory:
                system_parts.append(agent.backstory)
            system_message = " ".join(system_parts) if system_parts else ""

            agent_tool_vars = []
            for tool_key in agent.tools:
                tool_var = f"{self._to_snake(tool_key)}_tool"
                agent_tool_vars.append(tool_var)

            agents_data.append(
                {
                    "var_name": var_name,
                    "name": agent.role,
                    "system_message": self._escape_string(system_message),
                    "tool_vars": agent_tool_vars,
                }
            )

        teams_data = []
        for key, team in self.reader.teams.items():
            agent_list = [
                agent_vars.get(ak, self._to_snake(ak)) for ak in team.agent_keys
            ]
            teams_data.append(
                {
                    "agents": agent_list,
                    "max_turns": team.max_turns,
                    "process": team.process,
                }
            )

        template = self.jinja_env.get_template("autogen_main.py.j2")
        code = template.render(
            system_name=self.reader.system_name,
            model=model,
            tools=tools_list,
            tools_config=tools_config,
            agents=agents_data,
            teams=teams_data,
        )

        self._write_file("main.py", code)

    # -----------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------

    @staticmethod
    def _escape_string(s: str) -> str:
        """Escape a string for use in Python source code."""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
