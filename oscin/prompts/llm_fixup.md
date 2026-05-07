You are an expert in agent systems and code generation. You will receive
auto-generated source code that was produced from an ontology (Turtle/RDF).
The code has the correct structural skeleton but contains known issues that
prevent it from running. Your task is to fix the code so it is syntactically
valid and runnable.

## Input

1) The populated ontology instance that describes the agentic system:
{{instance_data}}

2) The auto-generated skeleton code for the {{target_framework}} framework:
{{skeleton_code}}

## Known Issues in the Generated Code

The auto-generation pipeline systematically produces the following defects.
Fix ALL of them:

### All frameworks
- **Tool stubs**: Every tool function or `_run` method raises
  `NotImplementedError`. Replace with a plausible working implementation.
  If the tool calls an external API or service that cannot be replicated,
  return a sensible static or mock response so the program does not crash.

- **Missing method bodies**: Flow steps, node functions, or agent methods
  that contain only `pass`  # TODO: implement step logic` must be filled
  with real logic derived from the ontology (prompts, task descriptions,
  input/output wiring, etc.).

### CrewAI-specific
- **`@listen()` / `@router()` without arguments**: These decorators MUST
  reference the method they listen to or route from, e.g. `@listen(step_name)`
  or `@router(source_step)`. The skeleton omits the argument; you must add it
  based on the workflow structure in the ontology (nextStep, hasAssociatedTask
  relations).

- **`kickoff()` without inputs**: Crews are invoked with `crew.kickoff()` but
  the required `inputs=` dict is missing. Derive the correct inputs from the
  ontology (task descriptions, agent goals, state fields).

- **`@tool` decorator pattern lost**: The original code may use the
  `@tool("name")` function decorator pattern, but the skeleton uses a class
  inheriting from `BaseTool`. Convert back to the `@tool` decorator pattern
  if that matches the framework idiom, or keep the class pattern but
  implement `_run` properly.

- **UUID default factories**: State fields like `id: str = ""` should often be
  `id: str = Field(default_factory=lambda: str(uuid.uuid4()))`. Restore this
  if the ontology suggests it.

### LangGraph-specific
- **Return type errors**: Node functions return `{"messages": response.content}`
  (a string) instead of `{"messages": [response]}` (an AIMessage object in a
  list). The `add_messages` reducer expects BaseMessage objects. Fix ALL
  return statements in node functions.

- **Missing imports**: `Sequence`, `BaseMessage`, `HumanMessage`, `AIMessage`,
  `SystemMessage`, `operator` etc. are used in type annotations but never
  imported. Add ALL missing imports.

- **Missing graph edges**: Nodes may have no outgoing edge (dead-ends).
  Every node except the last must have an edge or conditional edge leading
  somewhere. Add missing `add_edge` and `add_edge(node, END)` calls based
  on the workflow described in the ontology.

- **Wrong `__main__` invocation**: The skeleton uses
  `app.invoke({"messages": ["Start the task."]})` which sends strings instead
  of HumanMessage objects. Fix to use proper HumanMessage objects and include
  any required initial state fields (topic, task, etc.) from the ontology.

### AutoGen-specific
- **Missing agent descriptions**: `AssistantAgent` is missing the
  `description=` parameter, which is critical for `SelectorGroupChat`.
  Derive a concise description from the agent's role/goal in the ontology.

- **Truncated system messages**: Agent system messages may be cut short
  (e.g. `"You are a helpful assistant."` instead of the full instructions).
  Restore the complete system message from the ontology (goal, backstory,
  agentRole, hasDescription).

- **Termination conditions**: `TextMentionTermination("TERMINATE")` or
  `TextMentionTermination("DEBATE_COMPLETE")` may be missing. Check the
  ontology for termination-related data and add the correct conditions.

- **Function parameter order**: Tool function signatures may have parameters
  in the wrong order or missing default values. Check the ontology and fix.

## Rules

1. Do NOT change the structural skeleton (agents, nodes, edges, classes,
   crews, teams) unless it is clearly wrong and the ontology provides the
   correct information.

2. Use the ontology instance data as the authoritative source for:
   - System prompts and agent instructions
   - Tool names, descriptions, and parameter schemas
   - Workflow step ordering and routing logic
   - State field types and default values
   - Termination conditions and max turns

3. Produce complete, runnable code. Every `raise NotImplementedError` and
   `pass  # TODO` must be replaced.

4. Ensure all imports are present and resolve correctly.

5. The code must pass `python -c "import ast; ast.parse(open('main.py').read())"`
   for every .py file.

## Output format

Respond with the fixed source code files.
For each file, use the following exact format (three dashes, space, file
path, space, three dashes, followed by a markdown code block):

--- <relative_file_path> ---
```<language>
<file_contents>
```

Do not ask for confirmation or clarifications. Do not include extraneous
explanations outside of the file blocks. Keep the response clean so it
can be automatically parsed.