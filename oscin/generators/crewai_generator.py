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
- ``models.py`` — Pydantic models for structured outputs

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

# Well-known external tool packages for import generation
EXTERNAL_TOOL_IMPORTS = {
    "SerperDevTool": "from crewai_tools import SerperDevTool",
    "ScrapeWebsiteTool": "from crewai_tools import ScrapeWebsiteTool",
    "FileReadTool": "from crewai_tools import FileReadTool",
    "DirectoryReadTool": "from crewai_tools import DirectoryReadTool",
    "CodeDocsSearchTool": "from crewai_tools import CodeDocsSearchTool",
    "WebsiteSearchTool": "from crewai_tools import WebsiteSearchTool",
    "TXTSearchTool": "from crewai_tools import TXTSearchTool",
    "CSVSearchTool": "from crewai_tools import CSVSearchTool",
    "DOCXSearchTool": "from crewai_tools import DOCXSearchTool",
    "PDFSearchTool": "from crewai_tools import PDFSearchTool",
    "MDXSearchTool": "from crewai_tools import MDXSearchTool",
    "PGSearchTool": "from crewai_tools import PGSearchTool",
    "GithubSearchTool": "from crewai_tools import GithubSearchTool",
    "YoutubeVideoSearchTool": "from crewai_tools import YoutubeVideoSearchTool",
    "BrowserbaseLoadTool": "from crewai_tools import BrowserbaseLoadTool",
    "EXASearchTool": "from crewai_tools import EXASearchTool",
    "GmailGetThread": "from langchain_community.tools.gmail.get_thread import GmailGetThread",
    "TavilySearchResults": "from langchain_community.tools.tavily_search import TavilySearchResults",
}


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

        # Generate Pydantic model files for structured outputs
        if self.reader.pydantic_models:
            self._generate_models()

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
        log.info(
            "CREWAI GENERATION COMPLETE — %d files written", len(self._created_files)
        )
        log.info("=" * 60)

        return self._created_files

    # -----------------------------------------------------------
    # Tool Generation
    # -----------------------------------------------------------

    def _is_external_tool(self, tool: ExtractedTool) -> bool:
        """Check if a tool is external (imported, not locally defined)."""
        # Check for hasReference "external:..." pattern
        if tool.implementation_ref.startswith("external:"):
            return True
        # Known external tools
        if tool.class_name in EXTERNAL_TOOL_IMPORTS:
            return True
        return False

    def _generate_tool(self, key: str, tool: ExtractedTool) -> None:
        """Generate a BaseTool subclass skeleton for locally defined tools."""
        # Skip external tools — they'll be imported directly
        if self._is_external_tool(tool):
            log.info("  [SKIP] External tool: %s (imported, not generated)", key)
            return

        class_name = tool.class_name

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
    description: str = """{tool.description}"""
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
                ftype = self._json_type_to_python(
                    finfo.get("type", "str") if isinstance(finfo, dict) else "str"
                )
                desc = finfo.get("description", "") if isinstance(finfo, dict) else ""
                if fname in required:
                    lines.append(f'    {fname}: {ftype} = Field(description="{desc}")')
                else:
                    lines.append(
                        f'    {fname}: {ftype} = Field(default=None, description="{desc}")'
                    )

        return "\n".join(lines)

    # -----------------------------------------------------------
    # Pydantic Model Generation
    # -----------------------------------------------------------

    def _generate_models(self) -> None:
        """Generate a models.py file with Pydantic classes for structured outputs."""
        parts = [
            '"""',
            "Auto-generated Pydantic models for structured outputs.",
            '"""',
            "",
            "from typing import Optional",
            "from pydantic import BaseModel",
            "",
        ]

        for name, model in self.reader.pydantic_models.items():
            parts.append("")
            parts.append(f"class {name}(BaseModel):")
            if not model.fields:
                parts.append("    pass")
            else:
                for fname, ftype in model.fields.items():
                    py_type = self._json_type_to_python(
                        ftype if isinstance(ftype, str) else ftype.get("type", "str")
                    )
                    # Check if field is nullable
                    nullable = False
                    if isinstance(ftype, dict) and ftype.get("nullable"):
                        nullable = True
                    if nullable:
                        parts.append(f"    {fname}: Optional[{py_type}] = None")
                    else:
                        parts.append(f"    {fname}: {py_type}")
            parts.append("")

        self._write_file("models.py", "\n".join(parts))

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
            agent_dict: dict = {
                "role": agent.role if agent.role else agent_key,
                "goal": agent.goal if agent.goal else "",
            }
            if agent.backstory:
                agent_dict["backstory"] = agent.backstory
            agents_yaml[agent_key] = agent_dict

        agents_yaml_str = yaml.dump(
            agents_yaml,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )
        self._write_file(f"crews/{crew_snake}/config/agents.yaml", agents_yaml_str)

        # --- tasks.yaml ---
        tasks_yaml = {}
        for task_key in team.task_keys:
            task = self.reader.tasks.get(task_key)
            if not task:
                continue
            task_dict: dict = {
                "description": task.description if task.description else "",
            }
            if task.expected_output:
                task_dict["expected_output"] = task.expected_output
            if task.agent_key:
                task_dict["agent"] = task.agent_key
            tasks_yaml[task_key] = task_dict

        tasks_yaml_str = yaml.dump(
            tasks_yaml,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )
        self._write_file(f"crews/{crew_snake}/config/tasks.yaml", tasks_yaml_str)

        # --- Determine common LLM ---
        common_llm = self._detect_common_llm(team)

        # --- Build imports ---
        tool_imports = self._build_tool_imports(team)
        # Pydantic model imports
        model_imports = self._build_model_imports(team)

        process_str = (
            "Process.sequential"
            if team.process == "sequential"
            else "Process.hierarchical"
        )

        # Build @agent methods
        agent_methods = []
        for agent_key in team.agent_keys:
            agent = self.reader.agents.get(agent_key)
            if not agent:
                continue
            agent_methods.append(
                self._render_agent_method(agent_key, agent, common_llm)
            )

        # Build @task methods
        task_methods = []
        for task_key in team.task_keys:
            task = self.reader.tasks.get(task_key)
            if not task:
                continue
            task_methods.append(self._render_task_method(task_key, task))

        # Compose imports block
        all_imports = [
            "from crewai import Agent, Crew, Process, Task",
            "from crewai.project import CrewBase, agent, crew, task",
        ]
        if tool_imports:
            all_imports.extend(tool_imports)
        if model_imports:
            all_imports.extend(model_imports)
        imports_block = "\n".join(all_imports)

        # LLM class attribute
        llm_attr = ""

        code = f'''"""
Auto-generated CrewAI crew: {crew_class}
"""

{imports_block}


@CrewBase
class {crew_class}:
    """{crew_class}"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"{llm_attr}

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

    def _detect_common_llm(self, team: ExtractedTeam) -> Optional[str]:
        """Detect if all agents in a team share the same LLM."""
        llms = set()
        for agent_key in team.agent_keys:
            agent = self.reader.agents.get(agent_key)
            if agent and agent.llm:
                llms.add(agent.llm)
        if len(llms) == 1:
            return llms.pop()
        return None

    def _render_agent_method(
        self, agent_key: str, agent: ExtractedAgent, common_llm: Optional[str]
    ) -> str:
        """Render a single @agent method."""
        extra_args = []

        # Tools
        tool_list = self._build_tool_list(agent.tools)
        if tool_list:
            extra_args.append(f"            tools=[{tool_list}],")

        # LLM — use string format
        if common_llm and agent.llm == common_llm:
            extra_args.append(f'            llm="{agent.llm}",')
        elif agent.llm:
            extra_args.append(f'            llm="{agent.llm}",')

        # Verbose
        if agent.verbose is not None:
            extra_args.append(f"            verbose={agent.verbose},")

        # Allow delegation
        if agent.allow_delegation is not None:
            extra_args.append(f"            allow_delegation={agent.allow_delegation},")

        # Reasoning
        if agent.reasoning is not None:
            extra_args.append(f"            reasoning={agent.reasoning},")
        if agent.max_reasoning_attempts is not None:
            extra_args.append(
                f"            max_reasoning_attempts={agent.max_reasoning_attempts},"
            )

        # Memory
        if agent.memory is not None:
            extra_args.append(f"            memory={agent.memory},")

        extra_str = ""
        if extra_args:
            extra_str = "\n" + "\n".join(extra_args)

        return f'''
    @agent
    def {agent_key}(self) -> Agent:
        return Agent(
            config=self.agents_config["{agent_key}"],{extra_str}
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

    def _build_tool_imports(self, team: ExtractedTeam) -> list[str]:
        """Build import statements for tools used by agents in this team."""
        imports = set()
        for agent_key in team.agent_keys:
            agent = self.reader.agents.get(agent_key)
            if not agent:
                continue
            for tool_key in agent.tools:
                tool = self.reader.tools.get(tool_key)
                if not tool:
                    continue
                class_name = tool.class_name

                if class_name in EXTERNAL_TOOL_IMPORTS:
                    imports.add(EXTERNAL_TOOL_IMPORTS[class_name])
                else:
                    imports.add(f"from tools.{class_name} import {class_name}")
        return sorted(imports)

    def _build_model_imports(self, team: ExtractedTeam) -> list[str]:
        """Build import statements for Pydantic models referenced by tasks."""
        model_names = set()
        for task_key in team.task_keys:
            task = self.reader.tasks.get(task_key)
            if (
                task
                and task.output_pydantic
                and task.output_pydantic in self.reader.pydantic_models
            ):
                model_names.add(task.output_pydantic)
        if model_names:
            names = ", ".join(sorted(model_names))
            return [f"from models import {names}"]
        return []

    def _build_tool_list(self, tool_keys: list[str]) -> str:
        """Build a comma-separated list of tool instantiations."""
        if not tool_keys:
            return ""
        parts = []
        for k in tool_keys:
            tool = self.reader.tools.get(k)
            if tool:
                parts.append(f"{tool.class_name}()")
            else:
                parts.append(f"{self._to_class_name(k)}()")
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
        crew_class_names: dict[str, str] = {}  # team_key → class_name
        for crew_ref in flow.crew_references:
            team = self.reader.teams.get(crew_ref)
            if team:
                snake = self._to_snake(team.team_class_name)
                crew_imports.append(
                    f"from crews.{snake}.{snake} import {team.team_class_name}"
                )
                crew_class_names[crew_ref] = team.team_class_name

        imports_str = "\n".join(crew_imports)

        # Build flow methods
        methods = []
        # Collect all method names for method-reference decorators
        method_names = [s.method_name for s in flow.steps]
        for step in flow.steps:
            methods.append(self._render_flow_step(step, method_names))

        state_fields_code = ""
        if flow.state_fields:
            lines = []
            for field_name, field_type in flow.state_fields.items():
                py_type = (
                    self._json_type_to_python(field_type)
                    if field_type not in ("str", "int", "float", "bool", "list", "dict")
                    else field_type
                )
                if py_type == "str":
                    lines.append(f'    {field_name}: {py_type} = ""')
                elif py_type == "list":
                    lines.append(f"    {field_name}: {py_type} = []")
                elif py_type == "dict":
                    lines.append(f"    {field_name}: {py_type} = {{}}")
                else:
                    lines.append(f"    {field_name}: {py_type} = None")
            state_fields_code = "\n".join(lines)
        else:
            state_fields_code = "    pass"

        code = f'''"""
Auto-generated CrewAI Flow: {flow_class}
"""

from typing import Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

{imports_str}


class {state_class}(BaseModel):
    """Flow state — customize fields as needed."""
{state_fields_code}


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

    def _render_flow_step(
        self, step: ExtractedFlowStep, all_method_names: list[str]
    ) -> str:
        """Render a single flow method with the appropriate decorator."""
        is_router = step.step_type == "router" or bool(
            step.return_values or step.edge_mapping
        )
        if step.step_type == "start":
            if step.dependencies:
                dec = f'@start("{step.dependencies[0]}")'
            else:
                dec = "@start()"
            body = self._render_step_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

        elif is_router:
            # @router takes a method reference to the preceding step
            if step.dependencies:
                arg = step.dependencies[0]
                # Use as method reference if it matches a known method
                if arg in all_method_names:
                    dec = f"@router({arg})"
                else:
                    dec = f'@router("{arg}")'
            else:
                dec = "@router()"
            body = self._render_router_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

        else:  # regular/listen
            if step.dependencies:
                arg = step.dependencies[0]
                # Use as method reference if it matches a known method,
                # otherwise use string (for router return values like "complete")
                if arg in all_method_names:
                    dec = f"@listen({arg})"
                else:
                    dec = f'@listen("{arg}")'
            else:
                dec = "@listen()"
            body = self._render_step_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

    def _render_step_body(self, step: ExtractedFlowStep) -> str:
        """Render the body of a flow step method."""
        if step.function_body:
            lines = step.function_body.strip().split("\n")
            indented = "\n".join(f"        {line}" for line in lines)
            return indented
        if step.calls_crew:
            team = self.reader.teams.get(step.calls_crew)
            if team:
                return (
                    f"        result = {team.team_class_name}().crew().kickoff()\n"
                    f"        return result"
                )
        return "        pass  # TODO: implement step logic"

    def _render_router_body(self, step: ExtractedFlowStep) -> str:
        """Render the body of a router step."""
        if step.function_body:
            # Dedent the stored body to remove common leading whitespace,
            # then re-indent to method body level (8 spaces)
            dedented = textwrap.dedent(step.function_body).strip()
            lines = dedented.split("\n")
            indented = "\n".join(f"        {line}" for line in lines)
            return indented
        elif step.return_values:
            conditions = []
            for rv in step.return_values:
                conditions.append(f'        # return "{rv}"')
            return (
                "\n".join(conditions)
                + "\n        pass  # TODO: implement routing logic"
            )
        return "        pass  # TODO: implement routing logic"

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
