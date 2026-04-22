# OSCIN Extraction & Generation Mapping Reference

**Scope.** This document is the authoritative per-framework reference for what the
deterministic OSCIN pipeline extracts from source code and regenerates from a TTL.
It covers only the AST-based parsers and Jinja/string generators under
`oscin/parsers/` and `oscin/generators/`. The LLM baseline
(`oscin/llm_extractor.py`, `oscin/llm_generator.py`, `oscin/prompts/`) is out of
scope.

Every claim carries a `file:lines` citation so it can be verified directly
against the code. Terminology:

| Term | Meaning |
|---|---|
| **IR** | The framework-neutral intermediate representation (`oscin/intermediate.py`: `ExtractedAgent`, `ExtractedTask`, `ExtractedTeam`, `ExtractedTool`, `ExtractedFlow`, `ExtractedFlowStep`, `ExtractedPydanticModel`) |
| **Populator** | `oscin/populator.py` — IR → TTL direction |
| **Reader**    | `oscin/reader.py`    — TTL → IR direction |
| **agentoscin:** | Ontology namespace prefix (full IRI in `ontology/agentoscin.ttl`) |
| **ex:**         | Instance namespace, default `http://example.org/` |

Pipeline overview (both directions):

```
 Source code --[parser]--> IR --[populator]--> TTL₁
                                               │
                                              (compare)
                                               │
 Source code'<--[generator]-- IR <--[reader]-- TTL₂
```

Populator and reader are **not strictly inverse**; the gaps per framework are
listed in each section's "Quirks, gaps, and non-idempotent transformations".

---

## Cross-cutting conventions

These apply to every framework; the per-framework sections only call them out
when there is a deviation.

### Instance URI construction

`populator._create_individual(prefix, key, cls)` (populator.py:923–927) builds:

```
ex:<prefix>_<_safe_id(key)>
```

`_safe_id` (populator.py:970–972) replaces `" "`, `"-"`, `"."` with `"_"`.
The parser uses the equivalent `ast_utils.safe_key` (ast_utils.py:180–182).

Reader strips the prefix to recover the IR key (e.g.
`ex:Agent_researcher → agent_key = "researcher"`, reader.py:215,265,375,490).

### Core ontology anchors (common to all frameworks)

| IR class | `rdf:type` | Populator line |
|---|---|---|
| `ExtractedAgent`              | `agentoscin:LLMAgent`       | populator.py:178 |
| `ExtractedTask`               | `agentoscin:Task`           | populator.py:352 |
| `ExtractedTeam`               | `agentoscin:Team`           | populator.py:472 |
| `ExtractedTool`               | `agentoscin:Tool`           | populator.py:158 |
| `ExtractedFlow`               | `agentoscin:Orchestration`  | populator.py:744 |
| `ExtractedFlowStep`           | `agentoscin:WorkflowStep`   | populator.py:778 |
| `ExtractedPydanticModel`      | `agentoscin:Schema`         | populator.py:403–413, 754–767 |
| System (`reader.system_name`) | `agentoscin:AgenticSystem`  | populator.py:880–899 |

Key shared literals:

- `dcterms:title` (`HAS_TITLE`) — human-readable name of any individual
- `dcterms:description` (`HAS_DESCRIPTION`) — free-text description
- `agentoscin:hasSourceFramework` — written by populator, value returned by
  `Parser.framework_name()` (`"CrewAI"`, `"LangGraph"`, `"AutoGen_v0.4"`)

### Coordination-pattern map (populator.py:485–507)

Used by all three frameworks when emitting `agentoscin:employsCoordinationPattern`
on a Team. `ExtractedTeam.coordination_pattern` is preferred; otherwise falls
back to `process`:

| IR value | Pattern URI constant |
|---|---|
| `"Sequential"`     | `COORD_SEQUENTIAL`     |
| `"Hierarchical"`   | `COORD_HIERARCHICAL`   |
| `"RoundRobin"`     | `COORD_ROUND_ROBIN`    |
| `"SelectorBased"`  | `COORD_SELECTOR_BASED` |
| `"Swarm"`          | `COORD_SWARM`          |
| `"ReActLoop"`      | `COORD_REACT_LOOP`     |
| `"Network"`        | `COORD_NETWORK`        |
| `"Custom"`         | `COORD_CUSTOM`         |
| fallback `process="sequential"` | `COORD_SEQUENTIAL` |
| fallback `process="hierarchical"` | `COORD_HIERARCHICAL` |
| otherwise          | `COORD_CUSTOM`         |

Reader (reader.py:411–425) inverts local name heuristically, tolerating the
`Hierachical` misspelling (typo preserved in historical TTLs).

### Termination conditions (populator.py:640–705)

Emitted as sub-individuals of the team (`hasTerminationCondition`). For IR list
entries in `ExtractedTeam.termination_conditions`, each dict `{"type": ..., ...}`
maps to:

| IR `type` | TTL class | Extra predicates |
|---|---|---|
| `"TurnLimit"`  | `agentoscin:TurnLimitTermination`      | `hasMaxTurns` (int) |
| `"EventBased"` | `agentoscin:EventBasedTermination`     | `hasTriggerExpression` (str) |
| `"Routing"`    | `agentoscin:RoutingTermination`        | — |
| `"Composite"`  | `agentoscin:CompositeTermination`      | `hasOperator` (`"OR"`/`"AND"`); nested `hasSubCondition` triples to child termination individuals |

Reader (reader.py:448–481) rebuilds TurnLimit / EventBased / Routing. **Composite
is not re-read** — see the AutoGen section for the workaround.

### Literal escaping in generators

- **Python docstrings.** Triple-quoted bodies escape only `"""` (varies by
  generator — see each framework).
- **Python string literals.** The LangGraph generator uses `repr()` for
  `SystemMessage(content=...)` to survive f-string fragments and backstories
  ending in a quote (langgraph_generator.py:363,426).
- `BaseCodeGenerator._escape_string` (autogen_generator.py:246–249, also in
  base) replaces `\` → `\\`, `"` → `\"`, `\n` → `\\n`. Used for
  `system_message`, `trigger_expression`, `task_string` in AutoGen templating.

### Pydantic / JSON-Schema typing

`args_schema_json` (on `ExtractedTool`) and `hasSchemaDefinition` (on Schemas)
are JSON strings. Reverse mapping for generation (JSON Schema → Python type):

```python
{"string":"str","integer":"int","number":"float",
 "boolean":"bool","array":"list","object":"dict"}
```

(langgraph_generator.py:302–309; autogen_generator.py:112–119;
crewai_generator.py:744–755).

---

# 1. CrewAI

## 1.1 Summary

- **Parser**: `oscin/parsers/crewai_parser.py` (961 lines)
- **Generator**: `oscin/generators/crewai_generator.py` (785 lines)
- **Template**: `oscin/generators/templates/crewai_main.py.j2` — present but
  **dead code**; the generator assembles `main.py` with f-strings
  (crewai_generator.py:588–619, 621–649).

CrewAI is the only framework with a **YAML-first** config convention
(`config/agents.yaml`, `config/tasks.yaml`) plus `@CrewBase` + `@agent` / `@task`
/ `@crew` decorators. The parser walks both the YAML files and the decorated
methods; the generator regenerates both.

Files produced by the generator:

| File | When | Writer |
|---|---|---|
| `tools/<Cls>.py` per non-external tool | always if tools | crewai_generator.py:165 |
| `models.py`                             | if Pydantic models | crewai_generator.py:231 |
| `crews/<snake>/config/agents.yaml`      | always               | crewai_generator.py:263 |
| `crews/<snake>/config/tasks.yaml`       | always               | crewai_generator.py:287 |
| `crews/<snake>/<snake>.py`              | always               | crewai_generator.py:370 |
| `main.py`                               | always               | crewai_generator.py:619 / 649 |

## 1.2 Extraction — CrewAI source → IR

### 1.2.1 Source-tree walk

| Scope | Pattern | crewai_parser.py |
|---|---|---|
| Pipeline | `_parse_tools → _parse_pydantic_models → _parse_crews → _parse_flow` | 76–85 |
| Tools    | `source_dir/tools/*.py`              | 99–109 |
| Models   | `source_dir.rglob("*.py")`, skip `*Input` | 242–258 |
| Crews    | `source_dir/crews/**/*.py`           | 271–281 |
| Flow     | `source_dir/main.py`                 | 605–611 |

### 1.2.2 Tools

**`BaseTool` subclasses** (`_extract_basetool_subclasses`, lines 111–181):

| AST pattern | IR field |
|---|---|
| `class Foo(BaseTool):`                                 | `ExtractedTool.class_name = node.name` |
| `name: str = "Foo Tool"` (`ast.AnnAssign`)             | `.name` (falls back to class name) |
| `description: str = "..."`                             | `.description` |
| `args_schema: Type[BaseModel] = FooInput`              | `.args_schema_json` — resolved via a local-file Pydantic pre-scan (122–126, 898–905); serialised to JSON, `"{}"` if unresolved |
| `_run` method                                          | `.implementation_ref = f"{module_path}.{node.name}._run"` (module path via `_filepath_to_module`, 954–961) |

**`@tool("Name")` decorated functions** (lines 183–230):

| AST pattern | IR field |
|---|---|
| `@tool("Name")` first arg                              | `.name` (default `node.name`) |
| `ast.get_docstring(node)`                              | `.description` |
| `args_schema_json`                                     | always `"{}"` |
| `.implementation_ref`                                  | `f"{module_path}.{node.name}"` (no `._run` suffix) |

### 1.2.3 Pydantic models (`_parse_pydantic_models`, 237–258)

`class X(BaseModel)` at top level, with `*Input` skipped. Uses
`ast_utils.extract_pydantic_fields` (ast_utils.py:145–161) for
`{name: {"type": <ast.unparse>, "description": ...}}`.

### 1.2.4 CrewBase / agents / tasks / crew

| Concept | AST pattern | IR fields | crewai_parser.py |
|---|---|---|---|
| `@CrewBase class FooCrew` | class decorator                 | `ExtractedTeam.team_class_name = node.name` | 283–381, 584 |
| `agents_config = "config/agents.yaml"` | `ast.Assign` string | YAML loaded, resolved relative to class file | 314–320, 328–334 |
| `tasks_config` | same | YAML loaded | 320–321, 335–341 |
| `llm = ChatOpenAI(model="gpt-4o")` or `llm = "gpt-4o"` | class attribute | `class_llm` used as default for `@agent` | 322–323 |
| `@agent` method → `Agent(...)` | method decorator + call | `ExtractedAgent` — see table below | 383–450 |
| `@task` method → `Task(...)`  | method decorator + call | `ExtractedTask` — see table below   | 452–535 |
| `@crew` method → `Crew(...)`  | method decorator + call | `ExtractedTeam` kwargs below        | 537–594 |

**Agent extraction** (`_extract_agent_from_method`, 383–450). YAML key resolved
by `_resolve_config_key` (759–770): matches `config=self.agents_config["key"]`
with fallback to the Python method name.

| Source | IR field |
|---|---|
| `method.name`                       | `ExtractedAgent.agent_key` (dict key) |
| YAML `role` (default = method name) | `.role` (via `_clean_yaml_string`, 908–912) |
| YAML `goal`                         | `.goal` |
| YAML `backstory`                    | `.backstory` |
| `tools=[ToolA(), var, Cls.method]`  | `.tools: list[str]` (`_extract_tool_references`, 795–830) |
| `llm="..."`                         | `.llm` |
| `llm=self.llm`                      | `.llm` ← `class_llm` via `_resolve_llm_from_call` (939–951) |
| `verbose=bool`                      | `.verbose` |
| `allow_delegation=bool`             | `.allow_delegation` |
| `reasoning=bool`                    | `.reasoning` |
| `max_reasoning_attempts=int`        | `.max_reasoning_attempts` |
| `memory=bool`                       | `.memory` |
| `knowledge=[Src(), var, Cls.method, "str"]` | `.knowledge_sources` (`_extract_knowledge_sources`, 772–793) |

Fields never set by the CrewAI parser (dataclass defaults): `agent_type =
"GeneralPurpose"`, `description`, `directive_function = "DualDirective"`,
`reasoning_origin`, `memory_type`, `memory_persistence`, `human_input = False`.

**Task extraction** (`_extract_task_from_method`, 452–535):

| Source | IR field |
|---|---|
| YAML `description`         | `ExtractedTask.description` |
| YAML `expected_output`     | `.expected_output` |
| YAML `agent`               | `.agent_key` |
| `output_pydantic=SomeModel`| `.output_pydantic` |
| `output_json=SomeModel`    | `.output_json` (**dropped** by populator — see §1.5) |
| `tools=[...]`              | `.tools` |
| `human_input=True`         | `.human_input` |
| `context=[self.task_a(), task_b]` | `.context_tasks` |
| `guardrail=...`, `guardrails=[...]` | `.guardrails` — see §1.2.5 |
| `guardrail_max_retries=N`  | **dropped** (not on IR dataclass) |
| agent_key presence         | `.delegation_strategy = "ExplicitAssignment"` if set else `""` |

**Crew extraction** (`_extract_crew_config`, 537–594). Only the first
`Crew(...)` inside each `@crew` method is inspected.

| AST pattern | IR field |
|---|---|
| list of `@agent` method names | `ExtractedTeam.agent_keys` (AST order) |
| list of `@task` method names  | `.task_keys` (AST order) |
| `process=Process.sequential \| .hierarchical` | `.process` (default `"sequential"`) |
| `verbose=bool`                | `.verbose` |
| `memory=bool`                 | `.memory` |
| `manager_llm="..."`           | `.manager_llm` |
| `manager_agent=Name`          | `.manager_agent` |
| `knowledge=[...]`             | `.knowledge_sources` (**empty `local_vars`**, so bare `Name` refs are NOT resolved, line 581) |

Never set: `max_turns`, `coordination_pattern`, `termination_conditions`.

### 1.2.5 Guardrail prefix convention (`_extract_guardrails`, 832–867)

CrewAI IR stores guardrails as **prefixed strings** so the populator can emit
structured triples and the generator can round-trip.

| AST in `guardrail=` / `guardrails=[...]` | Emitted IR string |
|---|---|
| `ast.Constant(str)`                 | `"LLMBased:<value>"`          |
| `ast.Name(id)`                      | `"FunctionBased:<id>"`        |
| `ast.Call` with `Name` func         | `"FunctionBased:<func.id>"`   |
| `ast.Call` with `Attribute` func    | `"FunctionBased:<func.attr>"` |
| anything else                       | `"FunctionBased:unknown"`     |

### 1.2.6 Flow (`_parse_flow`, 601–664 / `_extract_flow_step`, 666–742)

| AST pattern | IR field |
|---|---|
| `class X(Flow):` / `class X(Flow[State])` | `ExtractedFlow.class_name`, `.state_model` |
| `@start` / `@start("label")`              | step_type `"start"` |
| `@listen(...)`                            | step_type `"regular"` (from `"listen"`) |
| `@router(...)`                            | step_type `"conditional"` (from `"router"`) |
| Decorator args (constants/names)          | `step.dependencies` |
| `SomeCrewClass().crew().kickoff()` in body | `step.calls_crew = "SomeCrewClass"` (pattern `Name() → .crew() → .kickoff[_async]()`, 870–894) |
| `return "label"` / `return name` (conditional) | `step.return_values` |
| Full method body (conditional only)       | `step.function_body` (source-line slice, fallback `ast.unparse`) |
| Pydantic state model fields               | `flow.state_fields = {name: type_str}` |

## 1.3 IR → TTL (populator, CrewAI-produced IR)

Only paths the CrewAI parser actually exercises. All URIs use the `ex:` prefix.

### 1.3.1 Tool (`_populate_tools`, 156–169)

```
ex:Tool_<class_name>  a agentoscin:Tool ;
    dcterms:title            <name> ;
    dcterms:description      <description> ;
    agentoscin:hasInputSchema <args_schema_json> ;
    agentoscin:hasImplementationReference <impl_ref> .
```

### 1.3.2 Agent (`_populate_agents`, 176–343)

```
ex:Agent_<key> a agentoscin:LLMAgent ;
    agentoscin:agentID   <role> ;
    agentoscin:agentRole <role> ;
    agentoscin:agentType "GeneralPurpose" ;
    agentoscin:hasReasoningEnabled <reasoning> ;
    agentoscin:hasAgentGoal  ex:Goal_<key> ;           # only if goal
    agentoscin:agentPrompt   ex:AgentPrompt_<key> ;    # DualDirective branch, 236–257
    agentoscin:agentToolUsage ex:Tool_<tool_key> ;     # per tool
    agentoscin:useLanguageModel ex:LM_<llm> ;          # if llm
    agentoscin:hasAgentConfig  ex:Config_verbose_Agent_<key>        ;  # if verbose set
    agentoscin:hasAgentConfig  ex:Config_allow_delegation_Agent_<key> ; # if allow_delegation set
    agentoscin:employsReasoningPattern ex:ReasoningPattern_Unspecified ;  # if reasoning
    agentoscin:hasReasoningOrigin "FrameworkManaged" ;
    agentoscin:hasMaxReasoningAttempts <n> ;           # if set
    agentoscin:hasMemoryBinding ex:MemoryBinding_AgentPrivate_<key> ; # if memory
    agentoscin:hasKnowledge ex:KnowledgeBase_<kb> ;    # per entry
    agentoscin:hasHumanCheckpoint ex:HumanCheckpoint_<key> .    # only if human_input (never for CrewAI)
```

`ex:AgentPrompt_<key>` (populator.py:236–257) carries:
- `dcterms:description ← f"{role}: {goal}"` (or role alone)
- `agentoscin:promptContext ← backstory`
- `agentoscin:hasDirectiveFunction "DualDirective"`
- `agentoscin:hasSourceAttribute "role, goal, backstory"`

### 1.3.3 Task (`_populate_tasks`, 350–463)

```
ex:Task_<key> a agentoscin:Task ;
    agentoscin:hasExpectedOutput <expected_output> ;
    agentoscin:performedByAgent  ex:Agent_<agent_key> ;       # if agent_key
    agentoscin:hasDelegationStrategy <value> ;                # "ExplicitAssignment" if agent_key, else "OrchestratorDelegated"
    agentoscin:taskPrompt ex:TaskPrompt_<key> ;               # always
    agentoscin:taskToolUsage ex:Tool_<key> ;                  # per tool
    agentoscin:hasOutputSchema ex:Schema_<model> ;            # if output_pydantic matches a known model
    agentoscin:dependsOn  ex:Task_<dep> ;                     # per context_task
    agentoscin:hasDependencyType "ContextProviding" ;
    agentoscin:hasGuardrail ex:Guardrail_<key>_<i> ;          # per guardrail
    agentoscin:hasHumanCheckpoint ex:HumanCheckpoint_<key> .  # if human_input
```

Guardrail sub-individual (populator.py:428–446) branches on the IR prefix:

| IR prefix | Triples on `Guardrail_<key>_<i>` |
|---|---|
| `FunctionBased:<name>` | `hasGuardrailType "FunctionBased"`, `hasValidationLogic <name>` |
| `LLMBased:<text>`      | `hasGuardrailType "LLMBased"`, `dcterms:description <text>` |
| *(no prefix)*          | `dcterms:description <text>` |

### 1.3.4 Team (`_populate_teams`, 470–634)

```
ex:Team_<key> a agentoscin:Team ;
    dcterms:title <team_class_name> ;
    agentoscin:hasAgentMember ex:Agent_<k> ;                          # per agent
    agentoscin:employsCoordinationPattern <pattern_uri> ;             # see cross-cutting map
    agentoscin:hasTerminationCondition ex:Termination_<key> ;         # default TaskCompletionTermination
    agentoscin:hasWorkflowPattern ex:WorkflowPattern_<key> ;          # always
    agentoscin:hasTeamMemoryBinding ex:MemoryBinding_GroupShared_<key> ; # if memory
    agentoscin:hasKnowledge ex:KnowledgeBase_<kb> ;                   # per entry
    agentoscin:hasSystemConfig ex:Config_verbose_Team_<key> .         # if verbose

# per task, ordered:
ex:CrewStep_<team>_<task> a agentoscin:StartStep|WorkflowStep|EndStep ;
    dcterms:title <task_key> ;
    agentoscin:stepOrder "n"^^xsd:integer ;
    agentoscin:hasAssociatedTask ex:Task_<task> ;
    agentoscin:nextStep ex:CrewStep_<team>_<next> .
```

Implicit `task→dependsOn→prev_task` (with `hasDependencyType "Sequential"`) is
added for sequential teams when a task has no explicit `context_tasks`
(populator.py:572–596).

If `manager_llm` or `manager_agent` is set, an extra synthetic Manager
LLMAgent (`agent_type="Manager"`) is added as a team member (populator.py:600–618).

### 1.3.5 Flow (`_populate_flow`, 712–825)

```
ex:Orchestration_<class_name> a agentoscin:Orchestration ;
    dcterms:title <class_name> ;
    agentoscin:employsCoordinationPattern COORD_CUSTOM ;               # hard-coded
    agentoscin:hasOutputSchema ex:StateSchema_<class_name> ;           # if state_fields
    agentoscin:orchestratesTeam ex:Team_<crew_ref> ;                   # per crew_ref
    agentoscin:hasWorkflowPattern ex:FlowWorkflowPattern_<class_name> .

# per step:
ex:FlowStep_<method>  a agentoscin:WorkflowStep [, agentoscin:StartStep | agentoscin:ConditionalStep] ;
    dcterms:title <method> ;
    agentoscin:stepOrder "n"^^xsd:integer ;
    agentoscin:hasRoutingLogic   <function_body> ;          # if non-stub
    agentoscin:hasEdgeMapping    <json_mapping> ;           # only if edge_mapping (CrewAI: empty)
    agentoscin:hasDecoratorArgument <arg> ;                 # per non-method decorator arg
    agentoscin:nextStep ex:FlowStep_<target> .              # resolved via label_map

# dead-end steps additionally get:
ex:FlowStep_<method> a agentoscin:EndStep .
```

## 1.4 TTL → IR → CrewAI source (reader + generator)

### 1.4.1 Tool (reader `_read_tools`, 164–191 → generator `_generate_tool`, 124–165)

| Triple | IR field | Generator emit |
|---|---|---|
| `?t a agentoscin:Tool`                           | `ExtractedTool.class_name` | skipped if `_is_external_tool` (114–122); else `tools/<Cls>.py` with `class <Cls>(BaseTool)` |
| `dcterms:title`                                  | `.name`                    | `name: str = "..."` |
| `dcterms:description`                            | `.description`             | `description: str = "..."` + docstring |
| `agentoscin:hasInputSchema`                      | `.args_schema_json`        | `_generate_args_schema` emits `class <Cls>Schema(BaseModel)` |
| `agentoscin:hasImplementationReference`          | `.implementation_ref`      | written as a docstring comment + `NotImplementedError` |

`EXTERNAL_TOOL_IMPORTS` (crewai_generator.py:44–64) maps known class names to
their upstream `from ... import ...`. Unknown externals are still emitted as
local skeletons.

### 1.4.2 Agent (reader `_read_agents`, 197–286 → generator `_render_agent_method`, 383–438 + agents.yaml, 243–264)

| Triple | Reader → IR | Generator emit |
|---|---|---|
| `agentoscin:agentRole`              | `.role`      | `agents.yaml:role:` |
| `hasAgentGoal/dcterms:description`  | `.goal`      | `agents.yaml:goal:` |
| `agentPrompt/promptContext`         | `.backstory` | `agents.yaml:backstory:` |
| `useLanguageModel/dcterms:title`    | `.llm`       | `llm="..."` kwarg |
| `agentToolUsage`                    | `.tools`     | `tools=[<Cls>(), ...]` (imports via `EXTERNAL_TOOL_IMPORTS` or `from tools.<Cls> import <Cls>`) |
| `hasReasoningEnabled`               | `.reasoning` | `reasoning=<bool>` |
| `hasMaxReasoningAttempts`           | `.max_reasoning_attempts` | `max_reasoning_attempts=<n>` |
| `hasMemoryBinding` (presence)       | `.memory`    | `memory=<bool>` |
| `bindsMemory/dcterms:title`         | `.memory_type` | **not re-emitted** |
| `bindsMemory/hasPersistenceScope`   | `.memory_persistence` | **not re-emitted** |
| `hasKnowledge/dcterms:title`        | `.knowledge_sources` | `knowledge=[Src1(), Src2()]` (no imports) |
| `hasAgentConfig[configKey=verbose]` | `.verbose`   | `verbose=<bool>` |
| `hasAgentConfig[configKey=allow_delegation]` | `.allow_delegation` | `allow_delegation=<bool>` |

Method shape:

```python
@agent
def <agent_key>(self) -> Agent:
    return Agent(
        config=self.agents_config["<agent_key>"],
        <extra_args>
    )
```

### 1.4.3 Task (reader `_read_tasks`, 292–391 → generator `_render_task_method`, 440–459 + tasks.yaml, 265–287)

| Triple | Reader → IR | Generator emit |
|---|---|---|
| `hasExpectedOutput`                 | `.expected_output`       | `tasks.yaml:expected_output:` |
| `performedByAgent`                  | `.agent_key`             | `tasks.yaml:agent:` |
| `taskPrompt/promptInstruction`      | `.description`           | `tasks.yaml:description:` |
| `taskToolUsage`                     | `.tools`                 | **dropped** (generator has no branch) |
| `dependsOn`                         | `.context_tasks`         | `context=[self.<t>(), ...]` |
| `hasHumanCheckpoint` (presence)     | `.human_input`           | `human_input=True` |
| `hasDelegationStrategy`             | `.delegation_strategy`   | not re-emitted |
| `hasGuardrail` (with type tag)      | `.guardrails` (prefixed) | `_render_guardrail_arg` (see below) |
| `hasOutputSchema` (when Schema)     | `.output_pydantic` + `reader.pydantic_models` dict | `output_pydantic=<Model>` + `from models import <Model>` |

Guardrail re-emission (`_render_guardrail_arg`, 461–486):

| IR prefix | Emitted Python |
|---|---|
| `FunctionBased:<id>` | bare identifier (non-idents substituted with `validate`) |
| `LLMBased:<txt>`     | escaped string literal |
| *(other)*            | escaped string literal |

Single → `guardrail=X,`; multiple → `guardrails=[X, Y],`.

### 1.4.4 Team (reader `_read_teams`, 397–512 → generator `_generate_crew`, 237–370)

| Triple | Reader → IR | Generator emit |
|---|---|---|
| `dcterms:title`                     | `.team_class_name`       | class name + snake-cased file paths |
| `hasAgentMember`                    | `.agent_keys`            | `@agent` method order, agents.yaml keys |
| `employsCoordinationPattern`        | `.coordination_pattern`, `.process` | `Process.sequential` or `Process.hierarchical` (any `"custom"` → `hierarchical`) |
| `hasWorkflowPattern/hasWorkflowStep` | `.task_keys` (ordered)  | `@task` method order, tasks.yaml keys |
| `hasSystemConfig[configKey=verbose]`| `.verbose`               | `verbose=<bool>` inside `Crew(...)` |
| `hasTeamMemoryBinding` (presence)   | `.memory`                | **dropped** (generator never emits `memory=` on Crew) |
| `hasTerminationCondition`           | `.max_turns`, `.termination_conditions` | **dropped** for CrewAI |
| `hasKnowledge/dcterms:title`        | `.knowledge_sources`     | `knowledge=[Src()]` inside `Crew(...)` |

Crew method shape:

```python
@crew
def crew(self) -> Crew:
    return Crew(
        agents=self.agents,
        tasks=self.tasks,
        process=Process.sequential,   # or hierarchical
        verbose=True,
        knowledge=[Src1(), ...],
    )
```

### 1.4.5 Flow (reader `_read_flow`, 518–580 + `_read_flow_steps`, 582–709 → generator `_generate_main`, 540–619 + `_render_flow_step`, 651–738)

Decorator emission:

| IR step_type | Condition | Decorator emitted |
|---|---|---|
| `"start"`                          | has deps → `@start("<dep>")`; else `@start()` | 658–663 |
| `"router"` / `"conditional"`       | dep is a known method → `@router(<method_ref>)`; else `@router("<label>")` | 655–686 |
| `"regular"`                        | dep is a known method → `@listen(<method_ref>)`; else `@listen("<label>")` | 688–698 |

Body emission:

| Case | Body |
|---|---|
| `function_body` present                          | original source, re-indented to 8 spaces |
| `calls_crew` matches a known team                | `result = <CrewClass>().crew().kickoff(); return result` |
| router with `return_values`                      | commented-out `# return "<rv>"` hints + `pass` |
| otherwise                                        | `pass  # TODO: implement step logic` |

A crucial post-read heuristic (reader.py:560–565): **if there is exactly one
`orchestratesTeam` reference and a start/regular step has no `function_body`,
that step inherits `calls_crew = single_crew`**. This re-establishes the
generator's subgraph-kickoff pattern without a dedicated per-step ontology
edge.

When no Orchestration exists (`_generate_main_no_flow`, 621–649), the generator
picks the first team and emits `result = <CrewClass>().crew().kickoff();
print(result)` in a flat `main.py`.

## 1.5 CrewAI — quirks, gaps, and non-idempotent transformations

### Populator writes → reader drops (not consumed for regeneration)

| Triple | Fate |
|---|---|
| `agentoscin:agentType "GeneralPurpose"`              | reader never reads `agentType` |
| `agentoscin:Goal` intermediate URI                   | reader only reads the one-hop `hasAgentGoal/dcterms:description` |
| `agentoscin:promptInstruction` (composite `"role: goal"`) on AgentPrompt | dead — `promptContext` carries backstory only |
| `agentoscin:hasDirectiveFunction`, `hasSourceAttribute` | not read |
| `agentoscin:promptOutputIndicator` on TaskPrompt      | duplicates `hasExpectedOutput`; only the latter is read |
| `agentoscin:hasDependencyType` on `dependsOn`        | not read |
| `agentoscin:hasDelegationStrategy`                   | read into IR but never re-emitted |
| `agentoscin:hasCheckpointType`/`hasCheckpointPosition`/`isMandatory` | only presence is read; subtypes lost |
| `agentoscin:hasReference "external:<k>"` on tool stubs | **not read** — external-tool detection on regen relies on `impl_ref.startswith("external:")`, a different predicate (see below) |

### Parser writes IR → populator/generator ignore

- `ExtractedTask.output_json` — extracted, but `hasOutputSchema` is only
  populated from `output_pydantic`; JSON variant completely lost.
- `guardrail_max_retries` — extracted to a local var, never stored on IR.

### Asymmetric AST handling

| Case | Parser | Generator |
|---|---|---|
| Task `tools=[...]` | extracted | **not emitted** (`_render_task_method` has no tools branch) |
| Agent `llm=self.llm` | resolved via class-level `llm =` | always emits literal `llm="..."` string |
| `class_llm` class attribute | parsed into `class_llm` local | never re-emitted |
| `context=[self.task_a()]` | accepts both `Call→Attribute` and bare `Name` | always emits `self.<task>()` form |
| Tool refs `Cls.method` | resolved via `elt.attr` | only `<Cls>()` emitted |
| Tool refs `ToolClass(kw=v)` | class name captured | `<Cls>()` with no args |
| `@start` bare (no parens) | accepted | always emits `@start()` |
| `.kickoff_async()` | detected | always emits `.kickoff()` |

### Known non-idempotent transformations

1. **Task `tools` drop.** Source with `Task(tools=[X])` round-trips through
   populator + reader but the CrewAI generator never re-emits `tools=`. A
   second extraction yields empty `task.tools`.
2. **Team `memory=` drop.** `memory=True` at team level survives populator and
   reader (`team.memory=True`) but the CrewAI generator never emits it in
   `Crew(...)`. Second extraction sees `memory=False`.
3. **External-tool detection asymmetry.** Populator writes `agentoscin:hasReference "external:<k>"`
   on stub tools; reader does not read it. The generator's `_is_external_tool`
   test is instead `impl_ref.startswith("external:")` — but `impl_ref` carries
   the **module path** from the populator, not `external:`. In practice
   recognition relies on the `EXTERNAL_TOOL_IMPORTS` whitelist
   (crewai_generator.py:44–64); unknown externals are regenerated as local
   skeletons.
4. **Coordination pattern `"custom"`.** Reader can produce `process="custom"`;
   generator collapses it to `Process.hierarchical`.
5. **Flow coordination pattern always `COORD_CUSTOM`** (populator.py:750–751);
   reader maps it to `process="custom"` → generator → `hierarchical`.
   Flow process is therefore not round-tripped.
6. **Crew reference heuristic assumes a single team.** The reader only
   re-attaches `calls_crew` when there is exactly one `orchestratesTeam` edge.
   Flows with multiple crews lose per-step crew attribution.
7. **`kickoff_async` → `kickoff` rewrite.** Parser detects both forms, generator
   always emits the sync form.
8. **Manager agent degradation.** `manager_llm`/`manager_agent` creates a
   synthetic Manager LLMAgent in TTL. On regen the reader sees it as a normal
   LLMAgent and the generator has no branch to re-emit `manager_llm=` /
   `manager_agent=` in `Crew(...)`.
9. **YAML path is rewritten.** Original `agents_config=` paths (non-standard
   locations) are normalised to `config/agents.yaml`.
10. **YAML only carries `role` / `goal` / `backstory`** (agents) or
    `description` / `expected_output` / `agent` (tasks). Custom keys in the
    source YAML are discarded.
11. **Dormant Jinja template.** `templates/crewai_main.py.j2` is present in
    the tree but unused; the generator composes `main.py` with f-strings.

---

# 2. LangGraph

## 2.1 Summary

- **Parser**: `oscin/parsers/langgraph_parser.py` (1620 lines)
- **Generator**: `oscin/generators/langgraph_generator.py` (664 lines)
- **Templates**:
  - `langgraph_main.py.j2` — **dormant**; the generator composes `main.py` as a
    line list (langgraph_generator.py:127–269)
  - `langgraph_tools.py.j2` — **active**; used for `tools.py`

LangGraph is expressed as `StateGraph(...).add_node(...).add_edge(...).compile()`.
Everything else (per-agent LLM, per-agent tools via `bind_tools`, system
prompts via `SystemMessage`, routing functions) is recovered by walking the
node function bodies.

## 2.2 Extraction — LangGraph source → IR

### 2.2.1 Source collection (102–141)

Walks `*.py` and `*.ipynb` (with `nbformat`, skipping `%`/`!` lines and merging
cells with `\n\n`).

### 2.2.2 Module-level pre-passes

| Pattern | Effect | Lines |
|---|---|---|
| `llm = ChatOpenAI(model="…")` (also `ChatAnthropic`, `ChatOllama`, `AzureChatOpenAI`) | `self._module_llms[var] = model` | 59, 817–845 |
| `x = llm.bind_tools([t1, t2])` or `bind_tools(tools_var)` | `self._bound_tools[var] = {tool_names}`; `_resolve_tool_list_variable` resolves vars | 851–908 |
| `tool_node = ToolNode(...)` | `self._tool_node_vars.add(var)` — excluded from agent node detection | 173–181 |

### 2.2.3 StateGraph walk (183–290)

| AST pattern | IR effect |
|---|---|
| `StateGraph(State)`                                 | `graph_class_name = "StateGraph"`, `state_model = "State"` |
| `graph.add_node("n", func)`                         | `nodes["n"] = _NodeInfo(func_ref, source_file)` |
| `graph.add_node("tools", tool_node)`                | `_tool_node_names.add("tools")` — **no agent created** |
| `graph.set_entry_point("n")` or `add_edge(START, "n")` | `entry_points.append("n")` |
| `graph.set_finish_point("n")` or `add_edge("n", END)` | `finish_points.append("n")` |
| `graph.add_edge("a", "b")`                          | `edges.append(("a", "b"))` |
| `graph.add_conditional_edges("n", router, {...})`   | `conditional_edges.append(_ConditionalEdge(...))` — dict **or** list form accepted |

For `add_conditional_edges` without a mapping, `_infer_router_targets`
(1207–1257) reads the router's `Literal[...]` return annotation and `ast.Return`
constants/names.

### 2.2.4 Agent extraction from node functions (`_extract_agents_from_functions`, 1010–1090)

| Source | IR field | Notes |
|---|---|---|
| node function name match     | `ExtractedAgent.agent_key = safe_key(node_name)` | keyed on **node name**, not function name |
| —                            | `.role = node_name`                              | — |
| `ast.get_docstring(fn)`      | `.goal`                                          | — |
| `SystemMessage(content=…)` / `system_message = …` / `{"role": "system", "content": …}` | `.backstory` | `_extract_system_prompt`, Patterns 1/2/3 (914–979); `ast.literal_eval` first, `ast.unparse` fallback |
| `ChatOpenAI(model="…")` inside body                      | `.llm` | `_find_llm_in_function`, 1566–1586 |
| module-level LLM fallback                                | `.llm` | first `_module_llms` value |
| `model_with_tools.invoke(...)` (receiver in `_bound_tools`) | `.tools` | sorted list |
| single `_bound_tools` entry, no receiver                  | `.tools` | fallback |

Stub agents are created for node functions that never matched
(langgraph_parser.py:298–324): `role = node_name`, empty goal/backstory, tools
`[]`, llm = first module-level LLM.

### 2.2.5 Tools (`_extract_tools`, 1096–1153)

| AST pattern | IR field |
|---|---|
| `@tool def foo(a: int, b: str): "..."` | `ExtractedTool(class_name=node.name, name=node.name, description=docstring, args_schema_json=json.dumps(schema), implementation_ref=f"{filepath.stem}.{node.name}")` |
| `ToolNode([name, ...])` elt `ast.Name` | stubbed `ExtractedTool` with empty description |
| `ToolNode([StructuredTool.from_function(f, name="X"), ...])` | tool name from `name=` kwarg or first positional arg |

### 2.2.6 TypedDict state (1539–1564) & Pydantic models (1159–1201)

- TypedDict fields (e.g. `State.messages: Annotated[list, add_messages]`) →
  `flow.state_fields = {name: ast.unparse(annotation)}`. `Annotated[...]` is
  preserved verbatim.
- `class X(BaseModel)` → `self.pydantic_models[name]`.

### 2.2.7 Task synthesis (367–398)

| Source | IR field |
|---|---|
| `HumanMessage(content=…)` / `return {"messages": [("user", "…"), …]}` | `task.description` (raw string or `ast.unparse`d f-string) |
| `return {"key1": …, "key2": …}` dict literal | `task.expected_output = ",".join(keys)` |
| none | `task.description = f"Perform {role} responsibilities"` |

Task always has `delegation_strategy = "TopologyDetermined"` (a LangGraph-specific tag).

### 2.2.8 Checkpointer / memory (731–775)

| AST | IR effect |
|---|---|
| `compile(checkpointer=MemorySaver())` | `team.memory=True`, memory_type `"MemorySaver"`, persistence `"ThreadScoped"`, scope `"GroupShared"` |
| `compile(store=InMemoryStore())`       | same bool; memory_type = class name; persistence `"Persistent"`, scope `"SystemGlobal"` |

Only the **bool** `team.memory` is propagated — the specific class / persistence
tier is lost before populator runs. (See §2.5 for the consequence.)

### 2.2.9 `interrupt()` detection (781–811)

Any `interrupt(...)` call inside a node function → `agent.human_input = True`.

### 2.2.10 Coordination pattern classification (`_classify_coordination_pattern`, 685–725)

| Topology | `team.coordination_pattern` |
|---|---|
| No conditional edges AND ≥2 agent nodes                   | `"Sequential"` |
| Conditional edge targets include a ToolNode AND (END or agent) | `"ReActLoop"` |
| Conditional edge with ≥2 distinct agent targets (not END) | `"Hierarchical"` |
| Any other conditional edge                                | `"Custom"` |
| default                                                   | `"Sequential"` |

### 2.2.11 Team synthesis (419–445)

```python
ExtractedTeam(
    team_class_name      = "StateGraph",
    agent_keys           = [...],
    task_keys            = [...],
    process              = "sequential",        # always
    coordination_pattern = <classified>,
    termination_conditions = [{"type": "Routing"}],  # always
    memory               = bool(memory_type),
)
```

Team key: `f"langgraph_team_{len(self.teams)}"`.

### 2.2.12 Flow step construction (`_build_flow_steps`, 1263–1348)

| Classification | step_type | `dependencies` | Extras |
|---|---|---|---|
| `name in entry_points` | `"start"` | outgoing edges only | `function_body` if also router source |
| `name in router_sources` (and not entry) | `"router"` | `[]` | `return_values=list(mapping.keys())`, `edge_mapping=dict(mapping)`, `function_body=ast.unparse(body)` |
| otherwise | `"regular"` | `incoming` | — |

`_extract_router_function_body` (1350–1380) joins `ast.unparse(stmt)`, stripping
any leading string-constant docstring.

### 2.2.13 `create_react_agent(...)` (468–551)

Parser creates a standalone ReAct `ExtractedAgent` + `ExtractedTask` +
`ExtractedTeam(coordination_pattern="ReActLoop")`. The generator **does not**
re-emit `create_react_agent`; see §2.5.

## 2.3 IR → TTL (populator, LangGraph-produced IR)

See the cross-cutting section for the agent / task / team boilerplate. Items
particular to LangGraph:

```
ex:Orchestration_<class_name> a agentoscin:Orchestration ;
    dcterms:title <class_name> ;
    agentoscin:employsCoordinationPattern COORD_CUSTOM ;      # hard-coded
    agentoscin:hasOutputSchema ex:StateSchema_<class_name> ;  # if state_fields
    agentoscin:hasWorkflowPattern ex:FlowWorkflowPattern_<class_name> .

ex:StateSchema_<class_name> a agentoscin:Schema ;
    dcterms:title <state_model> ;
    agentoscin:hasSchemaDefinition "<json.dumps(state_fields)>" .

# team coord pattern IS written correctly on the Team (populator.py:484–507).
# Teams carry Routing termination for LangGraph (populator.py:666–670).
```

For each `ExtractedFlowStep`:

```
ex:FlowStep_<method> a agentoscin:WorkflowStep [, StartStep | ConditionalStep] ;
    dcterms:title <method> ;
    agentoscin:stepOrder "n"^^xsd:integer ;
    agentoscin:hasRoutingLogic   <function_body> ;      # if non-stub
    agentoscin:hasEdgeMapping    "<json_mapping>" ;     # LangGraph-specific
    agentoscin:nextStep ex:FlowStep_<target> .
```

Important: **`hasRoutingLogic` is emitted for start steps too** when a start
node is also a conditional-edge source (populator.py:792–800); this is what
enables "entry node with conditional edges" to round-trip.

**Memory persistence is hard-coded** `"Persistent"` inside `_bind_memory`
(populator.py:937) regardless of the IR's stored `memory_persistence` — so
`"ThreadScoped"` detected for MemorySaver is lost.

## 2.4 TTL → IR → LangGraph source

### 2.4.1 Reader → IR highlights

| TTL | Reader → IR | Notes |
|---|---|---|
| `Agent / Task / Team / Tool` triples | standard mapping | — |
| `Orchestration/hasOutputSchema` | `flow.state_model`, `flow.state_fields = json.loads(hasSchemaDefinition)` | (reader.py:533–543) |
| Flow steps | `method_name`, `function_body` (from `hasRoutingLogic`), `edge_mapping` (from `hasEdgeMapping`), `return_values` (from `nextStep`), `dependencies` (from `hasDecoratorArgument` + inverse `nextStep`) | **`step_type` vocabulary is `{"start", "conditional", "regular"}`** — never `"router"` |
| State fallback | `_synthesize_state` (reader.py:117–143): when no state_fields in TTL, fabricates `{task_key}_output: str` per task, else `shared_context: str` | Feeds generator's State class |

### 2.4.2 Generator — main.py (langgraph_generator.py:127–269)

The generator composes `main.py` by appending lines; the Jinja template is
bypassed. Import block:

| Condition | Imports |
|---|---|
| always | `import dotenv`, `from typing import Annotated, TypedDict`, `from langgraph.graph import END, START, StateGraph`, `dotenv.load_dotenv()`, `from langgraph.graph.message import add_messages`, `from langchain_openai import ChatOpenAI` |
| any team has `memory=True` | `from langgraph.checkpoint.memory import MemorySaver` |
| any agent has `backstory` | `from langchain_core.messages import SystemMessage, HumanMessage` |
| tools present | `from tools import <snake names>`, `from langgraph.prebuilt import ToolNode` |

State class (`_generate_state_class`, 275–315): respects `"messages"` from TTL if
present; else defaults to `messages: Annotated[list, add_messages]`. Other
fields are mapped through the JSON-Schema → Python type table; unknown
annotations pass through verbatim.

LLM + tool preamble:

```python
model = ChatOpenAI(model="<first agent.llm or 'gpt-4o'>")
tools = [<snake tool names>]
tool_node = ToolNode(tools)
# either:
model_with_tools = model.bind_tools(tools)            # if ALL agents have tools
# or (per agent):
<snake(agent_key)>_model = model.bind_tools([<tools>])  # if MIXED
```

Per-node function (`_render_node_function`, 321–415):

| Case | Emitted |
|---|---|
| `step.calls_crew` (subgraph placeholder) | `# TODO: ... <TeamName> ... return {"messages": []}` |
| `agent.goal` present | docstring `"""{goal}"""` (triple quotes pre-escaped) |
| `agent.backstory` present | `literal = repr(backstory); system_prompt = SystemMessage(content=<literal>)` — **repr() is critical** (see §2.5) |
| `task.description` has `{var}` placeholders | `{var} = state.get('{var}', '')` injection |
| task description starts with `f'` | `task_prompt = <desc>` (passthrough) |
| else non-fallback description | `task_prompt = f"""<desc>"""` |
| `task.expected_output` non-empty | `return {"key": response.content, ...}` |
| else | `return {"messages": [response]}` |
| model var | `"model"` / `"<snake>_model"` / `"model_with_tools"` depending on per-agent-tools config |

Router emission (`_render_router_function`, 454–490): generator emits BOTH the
node function AND a `route_<fn>` router when a step carries routing logic.
Body is re-indented via `textwrap.dedent().strip()`.

Graph wiring (`_generate_flow_graph`, 496–583):

| Step kind | Emitted |
|---|---|
| start step | `graph.add_edge(START, "<method>")` |
| start step with router logic | also `graph.add_conditional_edges("<method>", route_<fn>, {<mapping>})` |
| `conditional` (from reader) | `graph.add_conditional_edges("<source>", <router>, {<mapping>})` |
| `regular` | `graph.add_edge("<dep>", "<method>")` per dep |
| last-in-chain regular | `graph.add_edge("<method>", END)` |
| tool loopback (agent with tools) | `graph.add_edge("tools", "<method>")` |

Compile + entry point:

```python
app = graph.compile([checkpointer=MemorySaver()])   # only if any team.memory
if __name__ == "__main__":
    result = app.invoke({"messages": ["Start the task."]})
    print(result["messages"][-1].content)
```

### 2.4.3 Generator — tools.py (`langgraph_tools.py.j2`, used)

```python
from langchain_core.tools import tool

@tool
def {{ func_name }}({{ params }}) -> str:
    """
    {{ tool.name }}
    {{ tool.description }}
    """
    raise NotImplementedError("TODO: implement {{ tool.name }}")
```

Parameters typed via `_build_tool_params` (JSON-Schema → Python). Empty schema
→ `**kwargs`.

## 2.5 LangGraph — quirks, gaps, and non-idempotent transformations

### Fields written but never round-tripped

| Field | Where produced | Where lost |
|---|---|---|
| `.agent_type` / `.directive_function` / `.description` on agents | populator writes (agentType, hasDirectiveFunction, prompt subvariants) | reader never reads agentType / hasDirectiveFunction |
| `ExtractedAgent.source_file`, `ExtractedTask.source_file`, `ExtractedTeam.source_file`, `ExtractedTool.source_file`, `ExtractedFlow.source_file` | set by parser | no ontology property — lost |
| `team.memory_type` / `memory_persistence` (MemorySaver vs SqliteSaver, ThreadScoped vs Persistent) | detected by parser into local vars | only bool `team.memory` is stored; `_bind_memory` hard-codes `"Persistent"` |

### Asymmetric AST handling

| Case | Parser | Generator |
|---|---|---|
| `MessagesState` base | treated as plain `state_model`; no TypedDict fields | generator always emits its own `class State(TypedDict)` |
| `create_react_agent(...)` | produces `coordination_pattern="ReActLoop"` team | generator emits a plain `StateGraph` — re-extraction won't re-detect ReAct |
| Supervisor / swarm prebuilt helpers | not specifically detected | no dedicated emission |
| `StructuredTool.from_function(f, name="X")` | tool name resolved | generator emits plain `@tool def x()` in tools.py |
| Dotted `add_node("n", pkg.mod.fn)` | dotted func_ref preserved in `_NodeInfo` | generator emits a flat `def {snake(method)}(state)` |
| `set_entry_point` / `set_finish_point` | accepted | generator always emits `add_edge(START, …)` / `add_edge(…, END)` |
| list-form `add_conditional_edges("n", f, ["a", END])` | accepted as identity map | generator re-emits as dict form |
| `MemorySaver()` vs `SqliteSaver.from_conn_string(...)` | class name captured | always emits `MemorySaver()` |
| `bind_tools` chained on `ChatOpenAI(...)` | chain form falls into `pass` branch | generator always emits separate `model = …` + `model_with_tools = model.bind_tools(…)` |

### Escaping and round-trip fixes

- **`repr()`-based backstory fix** (langgraph_generator.py:363, 426). The
  parser's system-prompt extractor falls back to `ast.unparse` when
  `ast.literal_eval` fails, which preserves raw Python expressions (including
  f-strings and backstories ending in a quote). Using
  `literal = repr(agent.backstory)` → `SystemMessage(content={literal})` makes
  the emitted source always valid Python.
- **Goal → docstring**: `docstring = agent.goal.replace('"""', r'\"\"\"')` then
  wrapped in triple quotes (no `repr()`, so newlines survive as literal
  newlines).
- **JSON round-trip**: `args_schema_json`, `hasSchemaDefinition`, and
  `hasEdgeMapping` are all JSON via `json.dumps`/`json.loads`.
- **State annotation preservation**: parser stores `ast.unparse(annotation)` as
  a string; generator re-emits verbatim unless it matches a JSON-Schema bare
  name (in which case the Python type is substituted).

### Known non-idempotent transformations

1. **Router label collapse.** Parser emits `step_type="router"`; populator
   writes `ConditionalStep`; reader restores as `"conditional"` (never
   `"router"`). Generator's `"router"` branch is unreachable in normal
   roundtrips. Behaviour is preserved but the label diverges.
2. **Orchestration coordination pattern always `COORD_CUSTOM`** at populator
   time (populator.py:750–751); the authoritative pattern lives on the Team.
3. **State synthesis drift.** `_synthesize_state` fabricates `{task_key}_output`
   fields when TTL has no schema; subsequent runs will then re-extract those
   synthesised fields → state schema grows monotonically across roundtrips
   starting from a flow without a TypedDict.
4. **`expected_output` comma-joined keys.** Keys containing a `,` would be
   mis-split by the generator (not guarded).
5. **`create_react_agent` collapse.** After one roundtrip, the ReAct agent is
   re-emitted as a generic StateGraph node — second extraction classifies it
   as `"Sequential"` or `"Custom"`.
6. **Reader's "one crew → first step.calls_crew" heuristic** (reader.py:560–565)
   is inactive for pure LangGraph round-trips (`crew_references` is always
   empty) but still runs if the TTL came from a cross-framework scenario.
7. **Dormant main template.** `langgraph_main.py.j2` is not used by the
   generator; edits to it have no effect.

---

# 3. AutoGen (v0.4)

## 3.1 Summary

- **Parser**: `oscin/parsers/autogen_parser.py` (723 lines)
- **Generator**: `oscin/generators/autogen_generator.py` (249 lines)
- **Template**: `oscin/generators/templates/autogen_main.py.j2` (100 lines) —
  **active**, fully used

AutoGen v0.4 expresses agent teams as `AssistantAgent(...)` + a group-chat
class (`RoundRobinGroupChat`, `SelectorGroupChat`, `Swarm`, `MagenticOneGroupChat`,
`GroupChat`). Termination is a first-class value: instances can be combined
with `|` (OR) and `&` (AND).

## 3.2 Extraction — AutoGen v0.4 source → IR

### 3.2.1 LLM clients pre-pass (135–150)

```python
model_client = OpenAIChatCompletionClient(model="gpt-4o")
```

Only top-level `Name = Call` is recognised; stored as
`self.llm_clients[var] = model`.

### 3.2.2 FunctionTool pre-pass (156–189)

```python
tool_var = FunctionTool(func, description="…")
```

Records `self._function_tools[var] = (func_name, description)`; later used to
enrich tool descriptions and to resolve `tools=[tool_var]` on agents.

### 3.2.3 Tool FunctionDef extraction (195–225)

Top-level `ast.FunctionDef` (name not starting with `_` and not `main`) →
`ExtractedTool(class_name=node.name, name=node.name, description=<FunctionTool
desc or docstring>, args_schema_json=<Python → JSON Schema>, implementation_ref=f"{stem}.{name}")`.
FunctionTool's `description=` beats the function docstring.

### 3.2.4 Agents (234–368)

Gated by class name `∈ {"AssistantAgent", "UserProxyAgent"}`.

| AST | IR field | Transform |
|---|---|---|
| `name="x"` (or positional, or `target.id`) | `role` / `agent_key` (`safe_key`) | — |
| `system_message="…"` | `goal` + `backstory` | `_split_system_message` (655–673): first sentence up to `". "` → goal; remainder → backstory |
| `description="…"` | `description` | — |
| `human_input_mode ∈ {"ALWAYS","TERMINATE"}` or `UserProxyAgent` | `human_input=True` | — |
| `model_client=var` | `llm` | resolved via `self.llm_clients` |
| legacy `llm_config={"config_list":[{"model":"…"}]}` | `llm` | dict literal |
| `tools=[tool_var, ...]` | `tools` | each resolved through `_function_tools` |
| `memory=[Cls(...), ...]` | `memory=True`, `memory_type`, `memory_persistence` | mapped via `_MEMORY_PERSISTENCE = {"ListMemory": "ExecutionScoped", "ChromaDBVectorMemory": "Persistent", "RedisMemory": "Persistent"}` |
| LLM starts with o-series prefix | `reasoning=True`, `reasoning_origin="ModelNative"` | `_REASONING_MODELS = {"o1","o1-mini","o1-preview","o3","o3-mini","o3-pro"}` |
| `UserProxyAgent` | `agent_type="UserProxy"` | else `"GeneralPurpose"` |
| `system_message` truthy | `directive_function="ModelDirective"` | else `"DualDirective"` |

Fields never set by the AutoGen parser: `verbose=None`,
`allow_delegation=None`, `max_reasoning_attempts=None`, `knowledge_sources=[]`.

### 3.2.5 Termination pre-pass (`term_vars`, 387–413)

**Top-level children only** (`ast.iter_child_nodes`), requiring exactly
`ast.Assign` → 1 `ast.Name` target → `ast.Call` RHS. This is a deliberate
restriction so the parser can rely on a flat `var = Call()` shape.

| Pattern | `term_vars[var]` |
|---|---|
| `TextMentionTermination("APPROVE")`      | `{"type": "EventBased", "trigger": "APPROVE"}` |
| `MaxMessageTermination(5)` or `MaxMessageTermination(max_messages=5)` | `{"type": "TurnLimit", "max_turns": 5}` |
| `TextMessageTermination(...)` / `HandoffTermination(...)` / `ExternalTermination(...)` | `{"type": "EventBased", "trigger": <class name string>}` |

### 3.2.6 Composite termination (416–425 + `_extract_composite_termination`, 556–578)

Matches top-level `ast.Assign` with `ast.BinOp` RHS:

| Operator | `operator` |
|---|---|
| `ast.BitOr`  | `"OR"`  |
| `ast.BitAnd` | `"AND"` |

Operand resolution is **restricted**: only `ast.Name` operands already in
`term_vars`, or nested `ast.BinOp`s, are accepted. Inline `ast.Call` operands
are silently dropped. Consequently, the AutoGen template emits two named
variables and a second `Name | Name` assignment rather than inlining:

```python
termination     = MaxMessageTermination(5)
text_termination = TextMentionTermination("APPROVE")
termination     = termination | text_termination    # BinOp of Names — parseable
```

Both the flat children *and* the Composite dict itself are appended to the
team's `termination_conditions` (parser 477–482), so the populator emits each
primitive termination individual once plus a `CompositeTermination` linking
them.

### 3.2.7 Team (427–523)

Class match: `RoundRobinGroupChat | SelectorGroupChat | Swarm | MagenticOneGroupChat | GroupChat`.

| Kwarg | IR field |
|---|---|
| positional list / `participants=` / legacy `agents=` | `agent_keys` (resolved through `_var_to_agent_key`) |
| `max_turns=` (v0.4) / `max_round=` (legacy) | `max_turns` |
| `termination_condition=<Name>` | fetched from `term_vars` (Composite expanded) |
| `termination_condition=<Call>` | `_parse_termination_call` |

Coordination pattern:

| Class | `coordination_pattern` |
|---|---|
| `RoundRobinGroupChat` | `"RoundRobin"` |
| `SelectorGroupChat`   | `"SelectorBased"` |
| `Swarm`               | `"Swarm"` |
| `MagenticOneGroupChat`| `"Custom"` |
| `GroupChat`           | `"RoundRobin"` |
| (unknown)             | `"Custom"` |

Team key: `f"{class_name}_{len(self.teams)}"`. `process` always hard-coded to
`"sequential"`.

### 3.2.8 Flow (586–649)

| AST | IR |
|---|---|
| `<team>.run(task="…")` / `.run_stream(task=…)` / `.initiate_chat(other, "…")` | `ExtractedFlowStep(step_type="start", method_name=f"run_{caller}" or f"initiate_chat_{caller}_to_{target}", calls_crew=target or caller)` |
| `task=` string | `ExtractedTask(task_key=f"autogen_task_<i>", description=<task>, delegation_strategy="OrchestratorDelegated")` |

Flow class name is always `"AutoGenFlow"`.

## 3.3 IR → TTL (populator, AutoGen-produced IR)

See the cross-cutting section for the agent / team boilerplate. Items
particular to AutoGen:

**Agent prompt branching** (populator.py:197–235) — when
`directive_function == "ModelDirective"` (i.e. `system_message` was set):

```
ex:AgentPrompt_<key> a agentoscin:Prompt ;
    agentoscin:promptInstruction <goal> ;
    agentoscin:promptContext     <backstory> ;
    agentoscin:hasDirectiveFunction "ModelDirective" ;
    agentoscin:hasSourceAttribute   "system_message" .
```

If `.description` is also set, a second prompt individual is emitted:

```
ex:OrchestratorPrompt_<key> a agentoscin:Prompt ;
    agentoscin:promptInstruction <description> ;
    agentoscin:hasDirectiveFunction "OrchestratorDirective" ;
    agentoscin:hasSourceAttribute   "description" .
```

Both are attached via `agentoscin:agentPrompt`.

**Memory** (AgentPrivate scope for AutoGen):

```
ex:MemoryBinding_AgentPrivate_<key> a agentoscin:MemoryBinding ;
    agentoscin:hasMemoryScope       "AgentPrivate" ;
    agentoscin:bindsMemory          ex:Memory_AgentPrivate_<key> .

ex:Memory_AgentPrivate_<key>        a agentoscin:Memory ;
    dcterms:title                   <memory_type> ;       # "ListMemory", "ChromaDBVectorMemory", …
    agentoscin:hasPersistenceScope  <memory_persistence>.
```

**Human checkpoint** (UserProxyAgent or explicit `human_input_mode`):

```
ex:HumanCheckpoint_<key> a agentoscin:HumanCheckpoint ;
    agentoscin:hasCheckpointType <"InputRequest" if UserProxy else "Approval"> ;
    agentoscin:isMandatory       true .
```

**Termination conditions.** See the cross-cutting termination table
(populator.py:640–705). AutoGen can emit every variant (TurnLimit, EventBased,
Routing, Composite with `hasOperator` + `hasSubCondition`).

## 3.4 TTL → IR → AutoGen source

### 3.4.1 Reader specifics (reader.py:448–481)

Termination reconstruction — extended so `hasTriggerExpression` survives
round-trips:

| rdf:type | IR entry appended |
|---|---|
| `TurnLimitTermination`  | `{"type": "TurnLimit", "max_turns": <hasMaxTurns>}` — also sets `team.max_turns` |
| `EventBasedTermination` | `{"type": "EventBased", "trigger": <hasTriggerExpression>}` |
| `RoutingTermination`    | `{"type": "Routing"}` |
| `CompositeTermination`  | **not read** — sub-conditions are recovered via the individual TurnLimit/EventBased siblings the populator emitted alongside |

### 3.4.2 Generator (autogen_generator.py)

Template variables (autogen_generator.py:132–240):

| Template var | Source |
|---|---|
| `system_name`            | `reader.system_name` |
| `model`                  | first unique `agent.llm` else `"gpt-4o"` |
| `tools`                  | snake-cased keys of `reader.tools` |
| `tools_config[*]`        | `{var_name, func_name, desc}` per tool (desc: `"` and `\n` stripped) |
| `agents[*].name`         | `agent.role.replace(" ", "_")` |
| `agents[*].system_message` | `_escape_string(" ".join([goal, backstory]))` |
| `agents[*].tool_vars`    | `[f"{snake(t)}_tool" for t in agent.tools]` |
| `agents[*].memory_class` | `agent.memory_type or ("ListMemory" if memory else "")` |
| `memory_classes`         | sorted unique set of memory classes |
| `teams[*].trigger_expression` | first `tc["trigger"]` from an EventBased entry (escaped) |
| `teams[*].max_turns`     | `team.max_turns` |
| `teams[*].pattern`       | `team.coordination_pattern` |
| `teams[*].process`       | `team.process` |
| `task_string`            | first task description (escaped) or `"Start the task."` |

### 3.4.3 Template (autogen_main.py.j2)

```python
import asyncio
import dotenv
dotenv.load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# {% if tools %}
from autogen_core.tools import FunctionTool
from tools import <tool names>
# {% endif %}
# {% if memory_classes %}
from autogen_core.memory import <classes>
# {% endif %}

model_client = OpenAIChatCompletionClient(model="<model>")

# -- Tools --
<var_name> = FunctionTool(<func>, description="…")

# -- Agents --
<var_name> = AssistantAgent(
    name="<role>",
    model_client=model_client,
    tools=[<tool_vars>],        # only if tools
    memory=[<MemoryClass>()],   # only if memory
    system_message=("<escaped system message>"),
)

# -- Team --
termination = MaxMessageTermination(<max_turns or 10>)
# {% if trigger_expression %}
text_termination = TextMentionTermination("<trigger>")
termination      = termination | text_termination
# {% endif %}

team = SelectorGroupChat(participants=[...], model_client=model_client,
                         termination_condition=termination)   # if SelectorBased or hierarchical
# or
team = RoundRobinGroupChat(participants=[...], termination_condition=termination)

async def main():
    stream = team.run_stream(task="<task_string>")
    await Console(stream)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Two-variable + reassignment termination pattern is required: the parser's
`_extract_composite_termination` only accepts `ast.Name | ast.Name` BinOps. A
single-line `termination = MaxMessageTermination(5) | TextMentionTermination("X")`
would be **silently dropped** by the parser, losing both the `hasMaxTurns` and
the `hasTriggerExpression` triples. The roundtrip-stable form emits the two
conditions as separate named variables and then composes them.

### 3.4.4 tools.py (generator 64–126)

Per-tool skeleton:

```python
def <func_name>(<typed params>) -> str:
    """
    <tool.name>
    <tool.description (with `"""` escaped)>

    Implementation reference: <impl_ref>
    """
    raise NotImplementedError("TODO: implement <tool.name>")
```

Parameter typing comes from `args_schema_json` via `_build_tool_params`
(generator 102–126), which reverses the JSON-Schema → Python type table.
Missing or unparseable schema → `**kwargs`.

## 3.5 AutoGen — quirks, gaps, and non-idempotent transformations

### Populator writes → reader drops

| Triple | Fate |
|---|---|
| `agentoscin:agentType` (`"UserProxy"` / `"Manager"` / `"GeneralPurpose"`) | reader never reads `agentType`; `UserProxyAgent`-ness lost |
| second `agentPrompt` (`OrchestratorPrompt`, `hasSourceAttribute "description"`) | reader reads only the **last** `agentPrompt`'s `promptContext`; `description=` dropped |
| `hasDirectiveFunction` | not read — defaults to `"DualDirective"` on regen |
| `hasHumanCheckpoint` on agents | reader reads task-level human checkpoints only; agent-level lost |
| `CompositeTermination` + `hasOperator` + `hasSubCondition` | not read — primitives recovered only via the individual TurnLimit/EventBased children (AND vs OR collapses to template default OR) |
| `manager_llm` / `manager_agent` | the synthetic Manager LLMAgent is re-read as a regular agent, but `manager_llm` stays `None` → hierarchical manager LLMs do not round-trip |

### Asymmetric AST handling

| Case | Parser | Generator |
|---|---|---|
| Team class | 5 classes accepted | template emits only `RoundRobinGroupChat` or `SelectorGroupChat` — Swarm / MagenticOne / GroupChat collapse to RoundRobin unless pattern is `SelectorBased` or `process == "hierarchical"` |
| `TextMessageTermination` / `HandoffTermination` / `ExternalTermination` | stored as `EventBased` with `trigger = <class name>` literal | template always emits `TextMentionTermination("…")` → these class names come back as string-match triggers |
| `UserProxyAgent` | separate class; `agentType="UserProxy"`, `HumanCheckpoint "InputRequest"` | template always emits `AssistantAgent` |
| `memory=[Cls(collection_name=..., ...)]` | class name captured, instance args ignored | always emits `Cls()` — instance args permanently lost |
| `llm_config=` (legacy) | parser reads legacy dict | generator never emits legacy form |
| `.run()` / `.run_stream()` / `.initiate_chat()` | all three captured | template always emits `team.run_stream(task="…")` |

### Escaping

- `_escape_string` (generator 246–249): `\` → `\\`, `"` → `\"`, `\n` → `\\n`.
  Used for `system_message`, `trigger_expression`, `task_string`.
- Tool description inside template: `desc.replace('"', '\\"').replace("\n", " ")`
  (generator 148) — **newlines become spaces**.
- Tool description inside `tools.py` docstrings: `"""` → `\"\"\"` only;
  newlines are preserved as docstring lines.
- Agent `name` sanitisation: `agent.role.replace(" ", "_")` only (generator 178);
  leading digits or other non-identifier characters are not handled.

### Known non-idempotent transformations

1. **`TextMessageTermination()` / `HandoffTermination()` / `ExternalTermination()`
   collapse.** Their trigger becomes the class-name literal, which the template
   re-emits as `TextMentionTermination("HandoffTermination")`. Subsequent
   extraction sees it as a normal text-mention trigger.
2. **`UserProxyAgent` → `AssistantAgent`.** After one roundtrip, the class
   becomes AssistantAgent; `agent_type` resets to `"GeneralPurpose"`.
3. **`Swarm`, `MagenticOneGroupChat`, `GroupChat` collapse.** Unless the
   coordination pattern is `"SelectorBased"` or the process is `"hierarchical"`,
   all degrade to `RoundRobinGroupChat`.
4. **Default `MaxMessageTermination(10)`.** When TTL carries no termination at
   all, the template falls back to `MaxMessageTermination(10)`, adding a
   `hasTerminationCondition` + `hasMaxTurns` triple that was not in the TTL.
5. **Memory instance arguments lost.** `ChromaDBVectorMemory(collection_name="x")`
   round-trips as `ChromaDBVectorMemory()`.
6. **Memory fallback to ListMemory.** When a TTL has `MemoryBinding` but no
   `Memory.dcterms:title` (e.g. historical), the generator emits `ListMemory()`
   regardless of the original class.
7. **`llm_config` normalised to v0.4.** Legacy inputs are always re-emitted as
   `model_client=`.
8. **`system_message` split/rejoin.** `_split_system_message` splits on the
   first `". "` and the generator rejoins `goal + " " + backstory`. Stable
   after the first roundtrip; can change a space around the split sentence.
9. **Composite operator collapse.** Because the reader does not re-read
   `CompositeTermination`/`hasOperator`/`hasSubCondition`, only the OR-with-two-
   conditions pattern emitted by the template survives. AND composites or
   composites with >2 conditions are permanently flattened.
10. **Flow step naming stabilises after the first pass.** Parser derives
    `f"run_{caller}"` etc.; the generator never emits these methods (flat
    `main()` calls `team.run_stream`), so a second extraction always yields
    `run_team`.
11. **Tool-list order is non-deterministic.** Populator emits `agentToolUsage`
    as a set-valued property; reader iteration relies on rdflib graph ordering.
    Generated `tools=[...]` order may differ from the source.

---

# 4. Cross-framework summary of roundtrip fixes

These are the key fixes that keep the end-to-end
`source → TTL₁ → generated → TTL₂` pipeline close to `triple_f1 = 1.0`.

| Fix | Where | Reason |
|---|---|---|
| Reader reads back `reasoning_origin`, `memory_type`, `memory_persistence`, `knowledge_sources`, `delegation_strategy`, `guardrails`, `termination_conditions` | reader.py (many paths) | populator writes these; without symmetric reading, triple_f1 collapsed |
| `calls_crew` heuristic (single `orchestratesTeam` → first body-less start/regular step) | reader.py:560–565 | no per-step ontology edge for crew subgraph calls |
| `_render_guardrail_arg` with `FunctionBased:`/`LLMBased:` prefix convention | crewai_generator.py:461–486 | parser/generator need a symmetric prefix contract |
| Emit `knowledge=[Src()]` in CrewAI generator | crewai_generator.py | reader captured `knowledge_sources` that generator previously dropped |
| Emit `memory=[<MemoryClass>()]` and memory imports in AutoGen | autogen_generator.py:184–187 + template | preserves `hasMemoryBinding` + `Memory.dcterms:title` on roundtrip |
| Emit LangGraph `graph.compile(checkpointer=MemorySaver())` when any team has `memory=True` | langgraph_generator.py:125,141–142,251 | makes `hasTeamMemoryBinding` round-trip |
| LangGraph docstring = `agent.goal` (not `"Node: {m}"`) | langgraph_generator.py:344–354 | goal literal was being clobbered |
| LangGraph `SystemMessage(content=repr(backstory))` | langgraph_generator.py:363, 426 | `ast.unparse`d backstories could end in quotes or contain f-strings; `repr()` produces always-valid Python |
| AutoGen termination: two-variable + `termination = termination | text_termination` reassignment | autogen_main.py.j2:66–74 | parser only accepts `Name | Name` BinOps; inlined Call-Call is silently dropped |
| Reader reads `hasTriggerExpression` from `EventBasedTermination` into `termination_conditions` | reader.py:458–481 | was the missing link for AutoGen travel-planning roundtrip |
| Roundtrip pipeline uses the same `--system-name` for TTL₁ and TTL₂ | evaluation/pipelines/roundtrip.py:142 | using `<name>_roundtrip` mismatched the system URI on every triple, collapsing triple_f1 (while prop_f1 and ind_f1 remained 1.0) |

---

# 5. File map

| Concern | File |
|---|---|
| IR dataclasses                   | `oscin/intermediate.py` |
| Populator (IR → TTL)             | `oscin/populator.py` |
| Reader (TTL → IR)                | `oscin/reader.py` |
| Base generator (shared helpers)  | `oscin/generators/base_generator.py` |
| Shared AST helpers               | `oscin/parsers/ast_utils.py` |
| CrewAI parser / generator        | `oscin/parsers/crewai_parser.py`, `oscin/generators/crewai_generator.py` |
| LangGraph parser / generator     | `oscin/parsers/langgraph_parser.py`, `oscin/generators/langgraph_generator.py` |
| AutoGen parser / generator       | `oscin/parsers/autogen_parser.py`, `oscin/generators/autogen_generator.py` |
| Templates                        | `oscin/generators/templates/*.j2` (only `autogen_main.py.j2` and `langgraph_tools.py.j2` are live) |
| Ontology                         | `ontology/agentoscin.ttl` |
| Roundtrip pipeline               | `evaluation/pipelines/roundtrip.py` |
| Evaluation metrics               | `evaluation/metrics/*.py`, `oscin/evaluator.py` |
