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
        log.info("AUTOGEN GENERATION COMPLETE — %d files written",
                 len(self._created_files))
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
            lines.extend([
                "",
                f"def {func_name}({params}) -> str:",
                f'    """',
                f"    {tool.name}",
            ])
            if desc:
                for desc_line in desc.split("\n"):
                    lines.append(f"    {desc_line}")
            if tool.implementation_ref:
                lines.append(f"")
                lines.append(f"    Implementation reference: {tool.implementation_ref}")
            lines.extend([
                f'    """',
                f'    raise NotImplementedError("TODO: implement {tool.name}")',
                "",
            ])

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
        """Generate the main.py with AutoGen v0.4 agent setup."""
        lines = [
            '"""',
            f"Auto-generated AutoGen application: {self.reader.system_name}",
            '"""',
            "",
            "import asyncio",
            "",
            "from autogen_agentchat.agents import AssistantAgent",
            "from autogen_agentchat.teams import RoundRobinGroupChat",
            "from autogen_agentchat.ui import Console",
            "from autogen_ext.models.openai import OpenAIChatCompletionClient",
        ]

        # Tool imports
        if self.reader.tools:
            lines.extend([
                "from autogen_core.tools import FunctionTool",
                "",
            ])
            tool_funcs = ", ".join(self._to_snake(k) for k in self.reader.tools)
            lines.append(f"from tools import {tool_funcs}")
        lines.append("")

        # LLM client — collect unique models
        llm_models = set()
        for agent in self.reader.agents.values():
            if agent.llm:
                llm_models.add(agent.llm)

        model = next(iter(llm_models), "gpt-4o")
        lines.extend([
            f'model_client = OpenAIChatCompletionClient(model="{model}")',
            "",
        ])

        # FunctionTool wrapping
        if self.reader.tools:
            lines.append("# -- Tools --")
            for key, tool in self.reader.tools.items():
                func_name = self._to_snake(key)
                var_name = f"{func_name}_tool"
                desc = tool.description.replace('"', '\\"').replace("\n", " ")
                lines.extend([
                    f"{var_name} = FunctionTool(",
                    f"    {func_name},",
                    f'    description="{desc}",',
                    f")",
                ])
            lines.append("")

        # Agent instantiations
        lines.append("# -- Agents --")
        agent_vars: dict[str, str] = {}
        for key, agent in self.reader.agents.items():
            var_name = self._to_snake(key)
            agent_vars[key] = var_name

            # Build system message from goal + backstory
            system_parts = []
            if agent.goal:
                system_parts.append(agent.goal)
            if agent.backstory:
                system_parts.append(agent.backstory)
            system_message = " ".join(system_parts) if system_parts else ""

            # Build tools list for this agent
            agent_tool_vars = []
            for tool_key in agent.tools:
                tool_var = f"{self._to_snake(tool_key)}_tool"
                agent_tool_vars.append(tool_var)

            lines.extend([
                f"{var_name} = AssistantAgent(",
                f'    name="{agent.role}",',
                f"    model_client=model_client,",
            ])
            if agent_tool_vars:
                tools_str = ", ".join(agent_tool_vars)
                lines.append(f"    tools=[{tools_str}],")
            lines.extend([
                f'    system_message=(',
                f'        "{self._escape_string(system_message)}"',
                f"    ),",
                f")",
                "",
            ])

        # Team setup
        for key, team in self.reader.teams.items():
            agent_list = ", ".join(
                agent_vars.get(ak, self._to_snake(ak))
                for ak in team.agent_keys
            )
            var_name = self._to_snake(key)

            lines.append("# -- Team --")
            lines.append(f"team = RoundRobinGroupChat(")
            lines.append(f"    participants=[{agent_list}],")
            if team.max_turns is not None:
                lines.append(f"    max_turns={team.max_turns},")
            lines.extend([
                f")",
                "",
            ])

        # Async main function
        lines.extend([
            "",
            "async def main():",
            "    stream = team.run_stream(",
            '        task="Start the task."  # TODO: provide initial message',
            "    )",
            "    await Console(stream)",
            "    await model_client.close()",
            "",
            "",
            'if __name__ == "__main__":',
            "    asyncio.run(main())",
            "",
        ])

        self._write_file("main.py", "\n".join(lines))

    # -----------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------

    @staticmethod
    def _escape_string(s: str) -> str:
        """Escape a string for use in Python source code."""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
