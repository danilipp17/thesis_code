"""
autogen_generator.py
====================
AutoGen code generator for the OSCIN reverse pipeline.

Generates a single ``main.py`` with AutoGen agent instantiations,
GroupChat setup, and conversation initiation.

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


class AutoGenGenerator(BaseCodeGenerator):
    """
    Generates an AutoGen project from the intermediate representations.

    Output structure:
    - ``main.py`` — agent instantiations, GroupChat, and conversation flow
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
            desc = tool.description.replace('"""', '\\"\\"\\"')
            lines.extend([
                "",
                f"def {func_name}(**kwargs) -> str:",
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

    # -----------------------------------------------------------
    # Main Generation
    # -----------------------------------------------------------

    def _generate_main(self) -> None:
        """Generate the main.py with AutoGen agent setup."""
        lines = [
            '"""',
            f"Auto-generated AutoGen application: {self.reader.system_name}",
            '"""',
            "",
            "from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager",
            "",
        ]

        # Tool imports
        if self.reader.tools:
            tool_funcs = ", ".join(self._to_snake(k) for k in self.reader.tools)
            lines.append(f"from tools import {tool_funcs}")
            lines.append("")

        # LLM config — collect unique models
        llm_models = set()
        for agent in self.reader.agents.values():
            if agent.llm:
                llm_models.add(agent.llm)

        if llm_models:
            model = next(iter(llm_models))
            lines.extend([
                f'llm_config = {{"model": "{model}"}}',
                "",
            ])
        else:
            lines.extend([
                'llm_config = {"model": "gpt-4o"}  # TODO: configure model',
                "",
            ])

        # Agent instantiations
        agent_vars = {}
        for key, agent in self.reader.agents.items():
            var_name = self._to_snake(key)
            agent_vars[key] = var_name

            # Build system message from role + goal + backstory
            system_parts = []
            if agent.role:
                system_parts.append(f"Role: {agent.role}")
            if agent.goal:
                system_parts.append(f"Goal: {agent.goal}")
            if agent.backstory:
                system_parts.append(agent.backstory)

            system_message = "\n".join(system_parts) if system_parts else ""

            lines.extend([
                f"{var_name} = AssistantAgent(",
                f'    name="{agent.role}",',
                f'    system_message="""{system_message}""",',
                f"    llm_config=llm_config,",
                f")",
                "",
            ])

        # UserProxy for human interaction
        lines.extend([
            "user_proxy = UserProxyAgent(",
            '    name="user_proxy",',
            '    human_input_mode="NEVER",',
            "    code_execution_config=False,",
            ")",
            "",
        ])

        # GroupChat per team
        for key, team in self.reader.teams.items():
            agent_list = ", ".join(
                agent_vars.get(ak, self._to_snake(ak))
                for ak in team.agent_keys
            )
            var_name = self._to_snake(key)

            lines.extend([
                f"groupchat_{var_name} = GroupChat(",
                f"    agents=[user_proxy, {agent_list}],",
                f"    messages=[],",
                f"    max_round=10,",
                f")",
                "",
                f"manager_{var_name} = GroupChatManager(",
                f"    groupchat=groupchat_{var_name},",
                f"    llm_config=llm_config,",
                f")",
                "",
            ])

        # Tool registration — register on the agents that actually use them
        if self.reader.tools:
            lines.append("# Register tools")
            # Build a map of tool_key → set of agent variable names
            tool_to_agents: dict[str, list[str]] = {}
            for agent_key, agent in self.reader.agents.items():
                for tool_key in agent.tools:
                    tool_to_agents.setdefault(tool_key, []).append(
                        agent_vars.get(agent_key, self._to_snake(agent_key))
                    )

            for key, tool in self.reader.tools.items():
                func_name = self._to_snake(key)
                desc = tool.description.replace("\n", " ").replace('"', '\\"')
                # Register on agents that use this tool, or first agent as fallback
                registering_agents = tool_to_agents.get(key, [])
                if not registering_agents:
                    registering_agents = [next(iter(agent_vars.values()), "user_proxy")]

                for agent_var in registering_agents:
                    lines.extend([
                        f"{agent_var}.register_for_llm(",
                        f'    name="{func_name}",',
                        f'    description="{desc}",',
                        f")({func_name})",
                    ])
                lines.append(f"user_proxy.register_for_execution()({func_name})")
                lines.append("")

        # Conversation initiation
        lines.extend([
            "",
            'if __name__ == "__main__":',
        ])

        if self.reader.teams:
            first_team_key = next(iter(self.reader.teams))
            team_var = self._to_snake(first_team_key)
            lines.extend([
                f"    user_proxy.initiate_chat(",
                f"        manager_{team_var},",
                f'        message="Start the task.",  # TODO: provide initial message',
                f"    )",
            ])
        else:
            first_agent_var = next(iter(agent_vars.values()), "user_proxy")
            lines.extend([
                f"    user_proxy.initiate_chat(",
                f"        {first_agent_var},",
                f'        message="Start the task.",  # TODO: provide initial message',
                f"    )",
            ])

        lines.append("")

        self._write_file("main.py", "\n".join(lines))
