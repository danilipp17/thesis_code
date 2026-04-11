You are an expert in agent systems and ontology population.

You will be given:
1) An existing ontology file in Turtle format (agentoscin — Ontology-driven Source Code Interoperability for Agentic AI Frameworks)
{{ontology}}
2) The source code and configuration of an agent-based solution (with agents, tasks, tools, workflows, prompts, etc.)
{{source_code}}

Your task:

1. Study the ontology file.
   - Treat it as a fixed schema with all classes and properties already defined.
   - Do NOT add, modify, or remove any classes or properties in the schema!

2. Study the source code and configuration.
   - Extract all instance-level information needed to fully describe the solution (agents, tasks, tools, workflows, prompts, parameters, data/artifacts, etc.).

3. Populate the ontology with individuals based on the extracted information. The goal is that another LLM can reconstruct the agent solution from the ontology instances you create. Do not add source code because we do not know the target framework to recreate the agent solution, so keep the semantic meaning and logic instead.
   - Use ONLY the existing classes and properties from the ontology!
   - Create individuals for all relevant entities and connect them with the appropriate properties.
   - Preserve all information from the source code (including prompts, parameters, and important logic) as literals or links between individuals. Fidelity is important, do not change or condense information.

4. Important modeling guidelines:
   - Create an AgenticSystem individual as the top-level container. Use containsAgent, containsTeam, containsOrchestration to link it.
   - Set hasSourceFramework to the framework name (e.g. "CrewAI", "AutoGen", "LangGraph").
   - For each agent: create an LLMAgent with agentID, agentRole, agentType, agentPrompt (linked Prompt individual with promptInstruction and promptContext), hasAgentGoal (linked Goal individual), agentToolUsage, useLanguageModel, hasAgentConfig.
   - For each task: create a Task with taskPrompt (linked Prompt with promptInstruction and promptOutputIndicator), hasExpectedOutput, performedByAgent, hasDelegationStrategy.
   - For each tool: create a Tool with hasTitle, hasDescription, hasInputSchema, hasImplementationReference.
   - For teams/crews: create a Team with hasAgentMember, employsCoordinationPattern (Sequential or Custom), hasWorkflowPattern (linked WorkflowPattern with hasWorkflowStep chain using nextStep and stepOrder), hasTerminationCondition.
   - For orchestration/flows: create an Orchestration with hasWorkflowPattern, orchestratesTeam, employsCoordinationPattern.
   - For workflow steps: use StartStep, WorkflowStep, EndStep, ConditionalStep as appropriate. Link via nextStep and hasAssociatedTask.
   - For configs: create Config individuals with configKey and configValue. Link via hasAgentConfig, hasSystemConfig, etc.
   - For language models: create a LanguageModel individual with hasTitle and link via useLanguageModel.
   - Use the instance namespace prefix ex: for all created individuals.

5. If some aspects of the solution cannot be modeled with the current ontology:
   - Do NOT invent new classes or properties!
   - Do NOT model programming information (e.g., specific code structures, language-specific constructs, or implementation details), we are interested in the semantic meaning. Do NOT model framework specific functions and SDKs! Do NOT model UI components!
   - Model them as closely as possible with the existing schema but do not abuse the schema.
   - If concepts are missing: list any missing concepts, limitations, or necessary extensions in an "Issues / Assumptions" comment block at the top of the Turtle output.

Output format:

- Respond ONLY with the instance information in .ttl format. Do not include any explanation before or after the Turtle content.
- Use the following prefixes:
  @prefix agentoscin: <http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/> .
  @prefix ex: <{{instance_namespace}}> .
  @prefix owl: <http://www.w3.org/2002/07/owl#> .
  @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
  @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
- Declare the output as an owl:Ontology that owl:imports the agentoscin base ontology.
- Do NOT reproduce the TBox (class and property declarations) — only output ABox (instance) triples.
- At the very top of the Turtle content, write a comment block:

  # Issues / Assumptions:
  # - <issue 1 or "No issues detected">
  # - <issue 2>
  # ...

  Do not ask for confirmation or clarifications, just produce the output as specified.
