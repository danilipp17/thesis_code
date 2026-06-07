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
import re
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

        # Ensure tools package has __init__.py
        if self.reader.tools:
            self._write_file("tools/__init__.py", "")

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
        # Fix #2: ``@tool``/``BaseTool`` reject an empty name string with
        # ``ValueError: OpenAI function name cannot be empty``. When the
        # ABox has no ``hasTitle`` for the tool, fall back to the class
        # name so the runtime accepts the registration.
        display_name = tool.name or class_name

        # Parse input schema for args
        args_code = self._generate_args_schema(tool.args_schema_json, class_name)

        code = f'''"""
Auto-generated tool: {display_name}
{tool.description}
"""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


{args_code}


class {class_name}(BaseTool):
    name: str = "{display_name}"
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
            "import dotenv",
            "from crewai import Agent, Crew, Process, Task",
            "from crewai.project import CrewBase, agent, crew, task",
            "",
            "dotenv.load_dotenv()",
        ]
        if tool_imports:
            all_imports.extend(tool_imports)
        if model_imports:
            all_imports.extend(model_imports)
        imports_block = "\n".join(all_imports)

        # LLM class attribute
        llm_attr = ""

        # Manager agent/llm for hierarchical crews
        manager_line = ""
        if team.manager_agent:
            snake_manager = self._to_snake(team.manager_agent)
            manager_line = f"\n            manager_agent=self.{snake_manager},"
        elif team.manager_llm:
            manager_line = f'\n            manager_llm="{team.manager_llm}",'

        # Team-level knowledge (re-extracted by parser via `knowledge=` kwarg)
        knowledge_line = ""
        if team.knowledge_sources:
            src_list = ", ".join(f"{s}()" for s in team.knowledge_sources)
            knowledge_line = f"\n            knowledge=[{src_list}],"

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
            verbose={team.verbose},{knowledge_line}{manager_line}
        )
'''
        self._write_file(f"crews/{crew_snake}/{crew_snake}.py", code)
        self._write_file(f"crews/{crew_snake}/__init__.py", "")

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
        method_name = self._to_snake(agent_key)

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

        # Knowledge sources (CrewAI Agent accepts `knowledge=[...]`).
        # The parser re-extracts these by walking `knowledge=` kwarg entries,
        # matching class Name() nodes. We emit as bare Call expressions so
        # round-trip extraction sees the same class names.
        if agent.knowledge_sources:
            src_list = ", ".join(f"{s}()" for s in agent.knowledge_sources)
            extra_args.append(f"            knowledge=[{src_list}],")

        extra_str = ""
        if extra_args:
            extra_str = "\n" + "\n".join(extra_args)

        return f'''
    @agent
    def {method_name}(self) -> Agent:
        return Agent(
            config=self.agents_config["{agent_key}"],{extra_str}
        )
'''

    def _render_task_method(self, task_key: str, task: ExtractedTask) -> str:
        """Render a single @task method."""
        method_name = self._to_snake(task_key)
        extra_args = ""
        if task.output_pydantic and task.output_pydantic in self.reader.pydantic_models:
            extra_args += f"\n            output_pydantic={task.output_pydantic},"
        if task.human_input:
            extra_args += "\n            human_input=True,"
        if task.context_tasks:
            ctx_refs = ", ".join(f"self.{self._to_snake(t)}()" for t in task.context_tasks)
            extra_args += f"\n            context=[{ctx_refs}],"
        if task.tools:
            tool_list = self._build_tool_list(task.tools)
            if tool_list:
                extra_args += f"\n            tools=[{tool_list}],"
        if task.guardrails:
            extra_args += f"\n            {self._render_guardrail_arg(task.guardrails)}"
        if task.guardrail_max_retries is not None:
            extra_args += (
                f"\n            guardrail_max_retries={task.guardrail_max_retries},"
            )

        return f'''
    @task
    def {method_name}(self) -> Task:
        return Task(
            config=self.tasks_config["{task_key}"],{extra_args}
        )
'''

    @staticmethod
    def _render_guardrail_arg(guardrails: list[str]) -> str:
        """
        Render the `guardrail=` / `guardrails=` kwarg for a CrewAI Task.

        Input format (from the populator / reader):
          - "FunctionBased:<name>" → bare Name reference (re-extracts as FunctionBased)
          - "LLMBased:<text>"      → string literal (re-extracts as LLMBased)
          - "<anything else>"      → string literal fallback
        """
        parts: list[str] = []
        for g in guardrails:
            if g.startswith("FunctionBased:"):
                name = g[len("FunctionBased:") :].strip() or "validate"
                if not name.isidentifier():
                    name = "validate"
                parts.append(name)
            elif g.startswith("LLMBased:"):
                detail = g[len("LLMBased:") :].replace("\\", "\\\\").replace('"', '\\"')
                parts.append(f'"{detail}"')
            else:
                detail = g.replace("\\", "\\\\").replace('"', '\\"')
                parts.append(f'"{detail}"')
        if len(parts) == 1:
            return f"guardrail={parts[0]},"
        return f"guardrails=[{', '.join(parts)}],"

    def _build_tool_imports(self, team: ExtractedTeam) -> list[str]:
        """Build import statements for tools used by agents or tasks in this team."""
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
        # Also include task-level tools
        for task_key in team.task_keys:
            task = self.reader.tasks.get(task_key)
            if not task:
                continue
            for tool_key in task.tools:
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
        state_class = flow.state_model if flow.state_model else f"{flow_class}State"

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
                # Preserve the source-level type annotation when it's already
                # a Python type expression (e.g. "List[Email]", "set[str]",
                # "Annotated[list, add_messages]"). Only fall through to the
                # JSON-schema mapping for primitive JSON-style names.
                ft = (field_type or "").strip()
                if ft in ("string", "integer", "boolean", "number", "array", "object"):
                    py_type = self._json_type_to_python(ft)
                else:
                    # Sanitize framework-specific types that don't exist in
                    # CrewAI/Pydantic context (e.g. LangGraph/LangChain types
                    # leaking through cross-framework translation).
                    py_type = self._sanitize_state_type(ft) or "Any"
                default = self._default_for_type(py_type)
                if default is None:
                    lines.append(f"    {field_name}: {py_type} = None")
                else:
                    lines.append(f"    {field_name}: {py_type} = {default}")
            state_fields_code = "\n".join(lines)
        else:
            state_fields_code = "    pass"

        code = f'''"""
Auto-generated CrewAI Flow: {flow_class}
"""

import dotenv
from typing import Any, Dict, List, Optional

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

dotenv.load_dotenv()

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

import dotenv

dotenv.load_dotenv()

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
        is_router = step.step_type in ("router", "conditional") or bool(
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
            # @router takes a method reference to the preceding step. Fix #6:
            # a bare ``@router()`` raises TypeError at decoration time, so
            # fall back to ``@start()`` when no predecessor is recorded.
            if step.dependencies:
                arg = step.dependencies[0]
                if arg in all_method_names:
                    dec = f"@router({arg})"
                else:
                    dec = f'@router("{arg}")'
            else:
                dec = "@start()"
            body = self._render_router_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

        else:  # regular/listen
            # Fix #6: a bare ``@listen()`` raises
            # ``TypeError: listen() missing 1 required positional argument:
            # 'condition'`` at decoration time. Fall back to ``@start()``.
            if step.dependencies:
                dec = f"@listen({self._render_decorator_args(step, all_method_names)})"
            else:
                dec = "@start()"
            body = self._render_step_body(step)
            return f"""
    {dec}
    def {step.method_name}(self):
{body}
"""

    def _render_decorator_args(self, step: ExtractedFlowStep, all_method_names: list[str]) -> str:
        """Render decorator arguments handling or_/and_ combinators."""
        deps = step.dependencies
        combinator = step.aggregation_combinator if hasattr(step, "aggregation_combinator") else ""
        if not deps:
            return ""

        def _fmt(dep: str) -> str:
            if dep in all_method_names:
                return dep
            return f'"{dep}"'

        formatted = [_fmt(d) for d in deps]
        if combinator in ("or_", "and_") and len(formatted) > 1:
            return f"{combinator}({', '.join(formatted)})"
        return formatted[0]

    @staticmethod
    def _rewrite_state_refs(body: str) -> str:
        """Fix #5: when a function body originates from a LangGraph node
        (``def node(state: AgentState): state['x']``), translate the bare
        ``state`` parameter into ``self.state`` so the CrewAI Flow method
        can access the flow's state correctly. The negative lookbehind
        avoids re-prefixing identifiers that already include ``state``
        as an attribute (``self.state``, ``my_state``) and the trailing
        lookahead restricts the match to subscript / attribute / call
        positions so identifiers like ``last_state`` or ``state_dict``
        are left alone.
        """
        # state['x']  -> self.state['x']
        # state.x     -> self.state.x
        # state.get(...) -> self.state.get(...)
        return re.sub(r"(?<![\w\.])state\b(?=\s*[\[\.\(])", "self.state", body)

    def _render_step_body(self, step: ExtractedFlowStep) -> str:
        """Render the body of a flow step method."""
        if step.function_body:
            body = self._rewrite_state_refs(step.function_body)
            lines = body.strip().split("\n")
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
            dedented = self._rewrite_state_refs(dedented)
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
    def _sanitize_state_type(ft: str) -> str:
        """Sanitize framework-specific type annotations for CrewAI/Pydantic.

        LangGraph/LangChain types like ``Annotated[Sequence[BaseMessage], add_messages]``
        are not valid in a CrewAI Flow state (Pydantic BaseModel). This method maps
        them to plain Python/Pydantic equivalents.
        """
        if not ft:
            return "Any"

        # Exact matches for common LangGraph state patterns
        _FRAMEWORK_TYPE_MAP = {
            "Annotated[Sequence[BaseMessage], add_messages]": "list",
            "Annotated[list, add_messages]": "list",
            "Annotated[Sequence[BaseMessage], operator.add]": "list",
            "Annotated[list, operator.add]": "list",
            "List[Union[HumanMessage, AIMessage]]": "list",
            "Sequence[BaseMessage]": "list",
            "list[BaseMessage]": "list",
        }
        if ft in _FRAMEWORK_TYPE_MAP:
            return _FRAMEWORK_TYPE_MAP[ft]

        # Pattern-based: anything with Annotated[..., add_messages/operator.add]
        if "Annotated[" in ft and ("add_messages" in ft or "operator." in ft):
            return "list"

        # Pattern-based: anything referencing BaseMessage/HumanMessage/AIMessage
        if any(msg in ft for msg in ("BaseMessage", "HumanMessage", "AIMessage")):
            return "list"

        return ft

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

    @staticmethod
    def _default_for_type(py_type: str) -> Optional[str]:
        """
        Pick a sensible Pydantic field default literal for a Python type.

        Heuristic on the textual form of the annotation: collection-like
        types get an empty-collection literal, scalars get their zero-value,
        anything else (including ``Annotated[...]``, custom classes, or
        ``Optional[X]``) returns ``None`` so the caller emits ``= None``.
        """
        t = (py_type or "").strip()
        low = t.lower()
        if low.startswith(("list", "list[", "list[")) or low.startswith("typing.list"):
            return "[]"
        if low.startswith(("dict", "dict[")) or low.startswith("typing.dict"):
            return "{}"
        if low.startswith(("set", "set[", "frozenset")) or low.startswith("typing.set"):
            return "set()"
        if low.startswith(("tuple", "tuple[")) or low.startswith("typing.tuple"):
            return "()"
        if low == "str":
            return '""'
        if low == "int":
            return "0"
        if low == "float":
            return "0.0"
        if low == "bool":
            return "False"
        return None
