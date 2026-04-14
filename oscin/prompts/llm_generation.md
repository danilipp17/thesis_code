You are an expert in agent systems, ontology-driven engineering, and code generation.

You will be given:
1) The base ontology schema in Turtle format:
{{ontology}}

2) A populated ontology instance containing an extracted agentic system:
{{instance_data}}

Your task:
1. Study the ontology instance data, which describes an agentic system (agents, tasks, tools, orchestrations, workflows, prompts, etc.).
2. Reconstruct and generate the complete, runnable source code for this agentic system using the {{target_framework}} framework.
3. Ensure the generated code accurately reflects all semantic relationships, configurations, and logic modeled in the ontology. If routing logic or prompts are specified, ensure they are integrated properly into the framework's idioms.
4. If some properties cannot be mapped exactly to the framework, implement the closest framework-idiomatic equivalent.

Output format:
Respond with the source code files required to run the system.
For each file, use the following exact format (three dashes, space, file path, space, three dashes, followed by a markdown code block):

--- <relative_file_path> ---
```<language>
<file_contents>
```

Example:
--- main.py ---
```python
print("Hello World")
```
--- crews/my_crew/config/agents.yaml ---
```yaml
my_agent:
  role: "..."
```

Do not ask for confirmation or clarifications. Do not include extraneous explanations outside of the file blocks. Keep the response clean so it can be automatically parsed.