"""
crewai_generator.py
===================
CrewAI code generator for the OSCIN reverse pipeline.

Reads the shared intermediate representations and generates a
complete CrewAI project structure including:

- ``main.py`` — Flow class with ``@start``, ``@listen``, ``@router``
- ``crews/<name>/<name>.py`` — ``@CrewBase`` class per team
- ``crews/<name>/config/agents.yaml`` — Agent configuration
- ``crews/<name>/config/tasks.yaml`` — Task configuration
- ``tools/<name>.py`` — ``BaseTool`` subclass skeleton per tool

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

from __future__ import annotations

import json
import logging
import textwrap
from pathlib import Path
from typing import Optional

import yaml

from oscin.generators.base_generator import BaseCodeGenerator
from oscin.intermediate import (
    ExtractedAgent,
    ExtractedFlow,
    ExtractedFlowStep,
    ExtractedTask,
    ExtractedTeam,
    ExtractedTool,
)

log = logging.getLogger("oscin")


class CrewAIGenerator(BaseCodeGenerator):
    """
    Generates a CrewAI project from the intermediate representations.
    """

    @staticmethod
    def framework_name() -> str:
        return "CrewAI"

    def generate(self) -> list[Path]:
        log.info("")
        log.info("=" * 60)
        log.info("GENERATING CREWAI SOURCE CODE")
        log.info("Output directory: %s", self.output_dir)
        log.info("=" * 60)

        # Generate tools first (crews may reference them)
        for key, tool in self.reader.tools.items():
            self._generate_tool(key, tool)

        # Generate each team as a crew package
        for key, team in self.reader.teams.items():
            self._generate_crew(key, team)

        # Generate main.py with the Flow class
        if self.reader.flow:
            self._generate_main(self.reader.flow)
        else:
            self._generate_main_no_flow()

        log.info("")
        log.info("=" * 60)
        log.info("CREWAI GENERATION COMPLETE — %d files written",
                 len(self._created_files))
        log.info("=" * 60)

        return self._created_files

    # -----------------------------------------------------------
    # Tool Generation
    # -----------------------------------------------------------

    def _generate_tool(self, key: str, tool: ExtractedTool) -> None:
        """Generate a BaseTool subclass skeleton."""
        class_name = self._to_class_name(key)

        # Parse input schema for args
        args_code = self._generate_args_schema(tool.args_schema_json, class_name)

        code = f'''"""
Auto-generated tool: {tool.name}
{tool.description}
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


{args_code}


class {class_name}(BaseTool):
    name: str = "{tool.name}"
    description: str = "{tool.description}"
    args_schema: Type[BaseModel] = {class_name}Schema

    def _run(self, **kwargs) -> str:
        """
        Implementation reference: {tool.implementation_ref}

        TODO: Implement tool logic here.
        """
        raise NotImplementedError(
            "Tool implementation must be provided. "
            "Original reference: {tool.implementation_ref}"
        )
'''
        self._write_file(f"tools/{class_name}.py", code)

    def _generate_args_schema(self, schema_json: str, class_name: str) -> str:
        """Generate a Pydantic model for the tool's args schema."""
        try:
            schema = json.loads(schema_json)
        except json.JSONDecodeError:
            return f"class {class_name}Schema(BaseModel):\n    pass"

        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        lines = [f"class {class_name}Schema(BaseModel):"]
        if not props:
            lines.append("    pass")
        else:
            for fname, finfo in props.items():
                ftype = self._json_type_to_python(finfo.get("type", "str") if isinstance(finfo, dict) else "str")
                desc = finfo.get("description", "") if isinstance(finfo, dict) else ""
                if fname in required:
                    lines.append(f'    {fname}: {ftype} = Field(description="{desc}")')
                else:
                    lines.append(f'    {fname}: {ftype} = Field(default=None, description="{desc}")')

        return "\n".join(lines)

    # -----------------------------------------------------------
    # Crew Generation
    # -----------------------------------------------------------

    def _generate_crew(self, key: str, team: ExtractedTeam) -> None:
        """Generate a @CrewBase class with agents.yaml and tasks.yaml."""
        crew_snake = self._to_snake(team.team_class_name)
        crew_class = team.team_class_name

        # --- agents.yaml ---
        agents_yaml = {}
        for agent_key in team.agent_keys:
            agent = self.reader.agents.get(agent_key)
            if not agent:
                continue
            agent_dict = {"role": agent.role, "goal": agent.goal}
            if agent.backstory:
                agent_dict["backstory"] = agent.backstory
            agents_yaml[agent_key] = agent_dict

        agents_yaml_str = yaml.dump(agents_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
        self._write_file(f"crews/{crew_snake}/config/agents.yaml", agents_yaml_str)

        # --- tasks.yaml ---
        tasks_yaml = {}
        for task_key in team.task_keys:
            task = self.reader.tasks.get(task_key)
            if not task:
                continue
            task_dict = {"description": task.description}
            if task.expected_output:
                task_dict["expected_output"] = task.expected_output
            if task.agent_key:
                task_dict["agent"] = task.agent_key
            tasks_yaml[task_key] = task_dict

        tasks_yaml_str = yaml.dump(tasks_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
        self._write_file(f"crews/{crew_snake}/config/tasks.yaml", tasks_yaml_str)

        # --- crew.py ---
        # Build imports
        tool_imports = self._build_tool_imports(team)
        process_str = "Process.sequential" if team.process == "sequential" else "Process.hierarchical"

        # Build @agent methods
        agent_methods = []
        for agent_key in team.agent_keys:
            agent = self.reader.agents.get(agent_key)
            if not agent:
                continue
            tool_list = self._build_tool_list(agent.tools)
            agent_methods.append(self._render_agent_method(agent_key, tool_list))

        # Build @task methods
        task_methods = []
        for task_key in team.task_keys:
            task = self.reader.tasks.get(task_key)
            if not task:
                continue
            task_methods.append(self._render_task_method(task_key, task))

        # Compose the crew file
        code = f'''"""
Auto-generated CrewAI crew: {crew_class}
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
{tool_imports}


@CrewBase
class {crew_class}:
    """{crew_class}"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

{"".join(agent_methods)}
{"".join(task_methods)}
    @crew
    def crew(self) -> Crew:
        """Creates the {crew_class}"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process={process_str},
            verbose={team.verbose},
        )
'''
        self._write_file(f"crews/{crew_snake}/{crew_snake}.py", code)

    def _render_agent_method(self, agent_key: str, tool_list: str) -> str:
        """Render a single @agent method."""
        tools_arg = f"\n            tools=[{tool_list}]," if tool_list else ""
        return f'''
    @agent
    def {agent_key}(self) -> Agent:
        return Agent(
            config=self.agents_config["{agent_key}"],{tools_arg}
        )
'''

    def _render_task_method(self, task_key: str, task: ExtractedTask) -> str:
        """Render a single @task method."""
        extra_args = ""
        if task.output_pydantic and task.output_pydantic in self.reader.pydantic_models:
            extra_args += f"\n            output_pydantic={task.output_pydantic},"
        if task.human_input:
            extra_args += "\n            human_input=True,"
        if task.context_tasks:
            ctx_refs = ", ".join(f"self.{t}()" for t in task.context_tasks)
            extra_args += f"\n            context=[{ctx_refs}],"

        return f'''
    @task
    def {task_key}(self) -> Task:
        return Task(
            config=self.tasks_config["{task_key}"],{extra_args}
        )
'''

    def _build_tool_imports(self, team: ExtractedTeam) -> str:
        """Build import statements for tools used by agents in this team."""
        imports = set()
        for agent_key in team.agent_keys:
            agent = self.reader.agents.get(agent_key)
            if not agent:
                continue
            for tool_key in agent.tools:
                class_name = self._to_class_name(tool_key)
                imports.add(f"from tools.{class_name} import {class_name}")
        if imports:
            return "\n".join(sorted(imports))
        return ""

    def _build_tool_list(self, tool_keys: list[str]) -> str:
        """Build a comma-separated list of tool instantiations."""
        if not tool_keys:
            return ""
        parts = [f"{self._to_class_name(k)}()" for k in tool_keys]
        return ", ".join(parts)

    # -----------------------------------------------------------
    # Main / Flow Generation
    # -----------------------------------------------------------

    def _generate_main(self, flow: ExtractedFlow) -> None:
        """Generate the main.py with a Flow class."""
        flow_class = flow.class_name
        state_class = f"{flow_class}State"

        # Build crew imports
        crew_imports = []
        for crew_ref in flow.crew_references:
            team = self.reader.teams.get(crew_ref)
            if team:
                snake = self._to_snake(team.team_class_name)
                crew_imports.append(
                    f"from crews.{snake}.{snake} import {team.team_class_name}"
                )

        imports_str = "\n".join(crew_imports)

        # Build flow methods
        methods = []
        for step in flow.steps:
            methods.append(self._render_flow_step(step))

        code = f'''"""
Auto-generated CrewAI Flow: {flow_class}
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

{imports_str}


class {state_class}(BaseModel):
    """Flow state — customize fields as needed."""
    pass


class {flow_class}(Flow[{state_class}]):
{"".join(methods)}

def kickoff():
    flow = {flow_class}()
    flow.kickoff()


if __name__ == "__main__":
    kickoff()
'''
        self._write_file("main.py", code)

    def _generate_main_no_flow(self) -> None:
        """Generate a simple main.py when there's no flow (just crews)."""
        # Pick the first team
        if not self.reader.teams:
            return

        team_key = next(iter(self.reader.teams))
        team = self.reader.teams[team_key]
        snake = self._to_snake(team.team_class_name)

        code = f'''"""
Auto-generated CrewAI entry point.
"""

from crews.{snake}.{snake} import {team.team_class_name}


def kickoff():
    result = {team.team_class_name}().crew().kickoff()
    print(result)


if __name__ == "__main__":
    kickoff()
'''
        self._write_file("main.py", code)

    def _render_flow_step(self, step: ExtractedFlowStep) -> str:
        """Render a single flow method with the appropriate decorator."""
        if step.decorator_type == "start":
            # @start decorator — may have a label arg
            if step.decorator_args:
                dec = f'@start("{step.decorator_args[0]}")'
            else:
                dec = "@start()"
            body = self._render_step_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

        elif step.decorator_type == "router":
            # @router — references the previous method
            # In CrewAI, @router takes a method reference, but since we
            # don't know the exact wiring, we use a generic form
            dec = f"@router({step.decorator_args[0]})" if step.decorator_args else "@router()"
            body = self._render_router_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

        else:  # listen
            if step.decorator_args:
                # @listen can take a string label or method ref
                arg = f'"{step.decorator_args[0]}"'
            else:
                arg = ""
            dec = f"@listen({arg})"
            body = self._render_step_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

    def _render_step_body(self, step: ExtractedFlowStep) -> str:
        """Render the body of a flow step method."""
        if step.calls_crew:
            team = self.reader.teams.get(step.calls_crew)
            if team:
                return (
                    f'        result = {team.team_class_name}().crew().kickoff()\n'
                    f'        return result'
                )
        return '        pass  # TODO: implement step logic'

    def _render_router_body(self, step: ExtractedFlowStep) -> str:
        """Render the body of a router step."""
        if step.function_body:
            # Indent the saved function body
            lines = step.function_body.strip().split("\n")
            indented = "\n".join(f"        {line}" for line in lines)
            return indented
        elif step.return_values:
            # Generate a simple routing skeleton
            conditions = []
            for rv in step.return_values:
                conditions.append(f'        # return "{rv}"')
            return "\n".join(conditions) + "\n        pass  # TODO: implement routing logic"
        return '        pass  # TODO: implement routing logic'

    # -----------------------------------------------------------
    # Type mapping helper
    # -----------------------------------------------------------

    @staticmethod
    def _json_type_to_python(json_type: str) -> str:
        """Map JSON Schema types to Python type annotations."""
        mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return mapping.get(json_type, "str")
