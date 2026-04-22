# Manual Mapping Reference — Source Code → AgentOSCI TTL

This document is the **hand-written specification** of how agentic framework
source code maps onto AgentOSCI ontology individuals. It is what a human would
write if they were transcribing a `Crew`, `StateGraph`, or `GroupChat` into RDF
by eye. The automated pipeline (`parsers/` + `intermediate.py` + `populator.py`)
is an implementation of exactly these rules.

Use this document as:

- The contract the parsers must satisfy.
- The reference when auditing a single example TTL by hand.
- The onboarding doc for "what does each triple mean?"

Companion document: [`extraction_generation_mapping.md`](./extraction_generation_mapping.md)
covers how the code performs this mapping. This document covers **what** the
mapping is, independent of implementation.

---

## 0. Conventions

### Prefixes

```turtle
@prefix :          <http://example.org/{system_name}#> .
@prefix agentoscin:<http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/> .
@prefix rdf:       <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd:       <http://www.w3.org/2001/XMLSchema#> .
```

### URI construction

Instance URIs follow the shape `:<Class>_<SafeKey>`, where `SafeKey` is the
source identifier with spaces, hyphens, and dots replaced by underscores.

| Source construct | Instance URI pattern | Example |
|---|---|---|
| Agent with key `researcher` | `:Agent_researcher` | `:Agent_researcher` |
| Task with key `write_section` | `:Task_write_section` | `:Task_write_section` |
| Tool with class name `WebSearchTool` | `:Tool_WebSearchTool` | `:Tool_WebSearchTool` |
| Team with class name `MyCrew` | `:Team_MyCrew` | `:Team_MyCrew` |
| Goal of agent `researcher` | `:Goal_researcher` | `:Goal_researcher` |
| LanguageModel `"gpt-4o"` | `:LM_gpt_4o` | `:LM_gpt_4o` |
| Task prompt of `write_section` | `:TaskPrompt_write_section` | `:TaskPrompt_write_section` |
| Agent prompt of `researcher` | `:AgentPrompt_researcher` | `:AgentPrompt_researcher` |
| Goal individual | `:Goal_<agent_key>` | `:Goal_researcher` |
| Schema individual | `:Schema_<class_name>` | `:Schema_BlogPost` |
| Workflow step (crew) | `:CrewStep_<team>_<task>` | `:CrewStep_MyCrew_research` |
| Workflow step (flow) | `:FlowStep_<method>` | `:FlowStep_kickoff` |
| Workflow pattern | `:WorkflowPattern_<team>` | `:WorkflowPattern_MyCrew` |
| Termination condition | `:EventTermination_<team>_<i>` | `:EventTermination_Chat_0` |
| Config entry | `:Config_<key>_<subject>` | `:Config_verbose_Agent_researcher` |
| MemoryBinding | `:MemoryBinding_<scope>_<key>` | `:MemoryBinding_AgentPrivate_researcher` |
| Memory | `:Memory_<scope>_<key>` | `:Memory_AgentPrivate_researcher` |
| Guardrail | `:Guardrail_<task>_<i>` | `:Guardrail_validate_output_0` |
| System | `:<system_name>` | `:tech_blog` |
| Orchestration | `:Orchestration_<flow_class>` | `:Orchestration_ContentPipeline` |

### Coordination pattern named individuals

These are **pre-declared in the ontology** — they are reused across all
instance graphs, never minted.

```
agentoscin:Sequential  agentoscin:Hierarchical  agentoscin:RoundRobin
agentoscin:SelectorBased  agentoscin:Swarm  agentoscin:ReActLoop
agentoscin:Network  agentoscin:Custom
```

---

## 1. Agent Mapping

### Ontology anchor

- Class: `agentoscin:LLMAgent` (subclass of `agentoscin:Agent`)
- Identity properties: `agentID`, `agentRole`, `agentType`
- Outgoing: `hasAgentGoal`, `agentPrompt`, `agentToolUsage`, `useLanguageModel`, `hasAgentConfig`, `hasMemoryBinding`, `employsReasoningPattern`, `hasKnowledge`, `hasHumanCheckpoint`

### Triple table (framework-neutral)

| Source concept | Subject | Predicate | Object | Object type |
|---|---|---|---|---|
| agent exists | `:Agent_<key>` | `rdf:type` | `agentoscin:LLMAgent` | class |
| stable source key | `:Agent_<key>` | `agentoscin:agentID` | `"<key>"` | xsd:string |
| human-readable role | `:Agent_<key>` | `agentoscin:agentRole` | `"<role>"` | xsd:string |
| agent type | `:Agent_<key>` | `agentoscin:agentType` | `"GeneralPurpose" \| "UserProxy" \| "Manager"` | xsd:string |
| reasoning flag | `:Agent_<key>` | `agentoscin:hasReasoningEnabled` | `true`/`false` | xsd:boolean |
| goal | `:Agent_<key>` | `agentoscin:hasAgentGoal` | `:Goal_<key>` | individual |
| goal text | `:Goal_<key>` | `agentoscin:hasDescription` | `"<goal text>"` | xsd:string |
| prompt | `:Agent_<key>` | `agentoscin:agentPrompt` | `:AgentPrompt_<key>` | individual |
| prompt text | `:AgentPrompt_<key>` | `agentoscin:promptInstruction` | `"<role: goal>"` or `"<system_message first sentence>"` | xsd:string |
| prompt context | `:AgentPrompt_<key>` | `agentoscin:promptContext` | `"<backstory>"` or `"<system_message rest>"` | xsd:string |
| directive function | `:AgentPrompt_<key>` | `agentoscin:hasDirectiveFunction` | `"DualDirective" \| "ModelDirective"` | xsd:string |
| LLM | `:Agent_<key>` | `agentoscin:useLanguageModel` | `:LM_<model>` | individual |
| LLM label | `:LM_<model>` | `agentoscin:hasTitle` | `"<model name>"` | xsd:string |
| tool binding | `:Agent_<key>` | `agentoscin:agentToolUsage` | `:Tool_<T>` | individual |
| verbose flag | `:Agent_<key>` | `agentoscin:hasAgentConfig` | `:Config_verbose_Agent_<key>` | individual |
| reasoning pattern | `:Agent_<key>` | `agentoscin:employsReasoningPattern` | `:ReasoningPattern_<Kind>` | individual |
| pattern class | `:ReasoningPattern_<Kind>` | `rdf:type` | `agentoscin:ReAct`/`ChainOfThought`/`ReflectionLoop`/`TreeOfThoughts`/`Unspecified` | class |

### Framework source — manual mapping

| Source snippet | Manual TTL (abbrev.) |
|---|---|
| **CrewAI**<br>`researcher = Agent(role="Researcher", goal="Find facts", backstory="…", llm="gpt-4o", tools=[SearchTool()])` | `:Agent_researcher a agentoscin:LLMAgent ; agentoscin:agentID "researcher" ; agentoscin:agentRole "Researcher" ; agentoscin:agentType "GeneralPurpose" ; agentoscin:hasAgentGoal :Goal_researcher ; agentoscin:agentPrompt :AgentPrompt_researcher ; agentoscin:useLanguageModel :LM_gpt_4o ; agentoscin:agentToolUsage :Tool_SearchTool .` |
| **LangGraph**<br>`researcher = create_react_agent(model="gpt-4o", tools=[web_search])` | `:Agent_researcher a agentoscin:LLMAgent ; agentoscin:agentID "researcher" ; agentoscin:agentRole "researcher" ; agentoscin:hasReasoningEnabled true ; agentoscin:hasReasoningOrigin "FrameworkManaged" ; agentoscin:employsReasoningPattern :ReasoningPattern_ReAct ; agentoscin:useLanguageModel :LM_gpt_4o ; agentoscin:agentToolUsage :Tool_web_search . :ReasoningPattern_ReAct a agentoscin:ReAct .` |
| **AutoGen**<br>`researcher = AssistantAgent(name="Researcher", system_message="You are a researcher. Be thorough.", model_client=client, tools=[search_tool])` | `:Agent_Researcher a agentoscin:LLMAgent ; agentoscin:agentID "Researcher" ; agentoscin:agentRole "Researcher" ; agentoscin:agentPrompt :AgentPrompt_Researcher ; agentoscin:useLanguageModel :LM_gpt_4o ; agentoscin:agentToolUsage :Tool_search_tool . :AgentPrompt_Researcher agentoscin:hasDirectiveFunction "ModelDirective" ; agentoscin:hasSourceAttribute "system_message" .` |

### Concrete worked example (CrewAI)

**Source** (`crews/content_crew/crew.py`):
```python
@agent
def researcher(self) -> Agent:
    return Agent(
        role="Tech Researcher",
        goal="Find credible sources on a given topic.",
        backstory="A PhD-level researcher with 10 years of experience.",
        llm="gpt-4o",
        tools=[SerperDevTool()],
        verbose=True,
        memory=True,
    )
```

**Manual TTL**:
```turtle
:Agent_researcher a agentoscin:LLMAgent ;
    agentoscin:agentID            "researcher" ;
    agentoscin:agentRole          "Tech Researcher" ;
    agentoscin:agentType          "GeneralPurpose" ;
    agentoscin:hasReasoningEnabled false ;
    agentoscin:hasAgentGoal       :Goal_researcher ;
    agentoscin:agentPrompt        :AgentPrompt_researcher ;
    agentoscin:useLanguageModel   :LM_gpt_4o ;
    agentoscin:agentToolUsage     :Tool_SerperDevTool ;
    agentoscin:hasAgentConfig     :Config_verbose_Agent_researcher ;
    agentoscin:hasMemoryBinding   :MemoryBinding_AgentPrivate_researcher .

:Goal_researcher a agentoscin:Goal ;
    agentoscin:hasDescription "Find credible sources on a given topic." .

:AgentPrompt_researcher a agentoscin:Prompt ;
    agentoscin:promptInstruction    "Tech Researcher: Find credible sources on a given topic." ;
    agentoscin:promptContext        "A PhD-level researcher with 10 years of experience." ;
    agentoscin:hasDirectiveFunction "DualDirective" ;
    agentoscin:hasSourceAttribute   "role, goal, backstory" .

:LM_gpt_4o a agentoscin:LanguageModel ;
    agentoscin:hasTitle "gpt-4o" .

:Config_verbose_Agent_researcher a agentoscin:Config ;
    agentoscin:configKey   "verbose" ;
    agentoscin:configValue "true" .

:MemoryBinding_AgentPrivate_researcher a agentoscin:MemoryBinding ;
    agentoscin:hasMemoryScope "AgentPrivate" ;
    agentoscin:bindsMemory    :Memory_AgentPrivate_researcher .

:Memory_AgentPrivate_researcher a agentoscin:Memory ;
    agentoscin:hasPersistenceScope "Persistent" .
```

---

## 2. Task Mapping

### Ontology anchor

- Class: `agentoscin:Task`
- Outgoing: `performedByAgent`, `taskPrompt`, `taskToolUsage`, `hasOutputSchema`, `dependsOn`, `hasGuardrail`, `hasHumanCheckpoint`
- Datatype: `hasExpectedOutput`, `hasDelegationStrategy`, `hasDependencyType`

### Triple table

| Source concept | Subject | Predicate | Object |
|---|---|---|---|
| task exists | `:Task_<key>` | `rdf:type` | `agentoscin:Task` |
| expected output | `:Task_<key>` | `agentoscin:hasExpectedOutput` | `"<string>"` |
| agent assignment | `:Task_<key>` | `agentoscin:performedByAgent` | `:Agent_<agent_key>` |
| delegation | `:Task_<key>` | `agentoscin:hasDelegationStrategy` | `"ExplicitAssignment" \| "OrchestratorDelegated" \| "TopologyDetermined"` |
| prompt | `:Task_<key>` | `agentoscin:taskPrompt` | `:TaskPrompt_<key>` |
| prompt text | `:TaskPrompt_<key>` | `agentoscin:promptInstruction` | `"<description>"` |
| prompt output indicator | `:TaskPrompt_<key>` | `agentoscin:promptOutputIndicator` | `"<expected_output>"` |
| tool | `:Task_<key>` | `agentoscin:taskToolUsage` | `:Tool_<T>` |
| output schema | `:Task_<key>` | `agentoscin:hasOutputSchema` | `:Schema_<Model>` |
| schema def | `:Schema_<Model>` | `agentoscin:hasSchemaDefinition` | `"<JSON Schema string>"` |
| dependency | `:Task_<key>` | `agentoscin:dependsOn` | `:Task_<other_key>` |
| dependency type | `:Task_<key>` | `agentoscin:hasDependencyType` | `"Sequential" \| "ContextProviding"` |
| guardrail | `:Task_<key>` | `agentoscin:hasGuardrail` | `:Guardrail_<key>_<i>` |

### Framework source — manual mapping

| Source snippet | Manual TTL (abbrev.) |
|---|---|
| **CrewAI**<br>`@task`<br>`def research(self) -> Task:`<br>`  return Task(description="Research X", expected_output="3 sources", agent=self.researcher(), guardrail=validate_output, guardrail_max_retries=3)` | `:Task_research a agentoscin:Task ; agentoscin:hasExpectedOutput "3 sources" ; agentoscin:performedByAgent :Agent_researcher ; agentoscin:hasDelegationStrategy "ExplicitAssignment" ; agentoscin:taskPrompt :TaskPrompt_research ; agentoscin:hasGuardrail :Guardrail_research_0 .` |
| **LangGraph**<br>*(tasks are synthesised one-per-agent; description comes from node docstring)* | `:Task_task_researcher a agentoscin:Task ; agentoscin:performedByAgent :Agent_researcher ; agentoscin:hasDelegationStrategy "TopologyDetermined" .` |
| **AutoGen**<br>`await team.run_stream(task="Write a blog post on X")` | `:Task_autogen_task_0 a agentoscin:Task ; agentoscin:taskPrompt :TaskPrompt_autogen_task_0 ; agentoscin:hasDelegationStrategy "OrchestratorDelegated" .` |

### Concrete worked example (CrewAI with guardrail)

**Source**:
```python
@task
def validate_summary(self) -> Task:
    return Task(
        description="Summarise the draft into 3 bullet points.",
        expected_output="Three bullet points, each ≤ 20 words.",
        agent=self.editor(),
        guardrail=check_bullet_count,
        guardrail_max_retries=2,
    )
```

**Manual TTL**:
```turtle
:Task_validate_summary a agentoscin:Task ;
    agentoscin:hasExpectedOutput      "Three bullet points, each ≤ 20 words." ;
    agentoscin:performedByAgent       :Agent_editor ;
    agentoscin:hasDelegationStrategy  "ExplicitAssignment" ;
    agentoscin:taskPrompt             :TaskPrompt_validate_summary ;
    agentoscin:hasGuardrail           :Guardrail_validate_summary_0 .

:TaskPrompt_validate_summary a agentoscin:Prompt ;
    agentoscin:promptInstruction     "Summarise the draft into 3 bullet points." ;
    agentoscin:promptOutputIndicator "Three bullet points, each ≤ 20 words." ;
    agentoscin:hasSourceAttribute    "description, expected_output" .

:Guardrail_validate_summary_0 a agentoscin:Guardrail ;
    agentoscin:hasGuardrailType    "FunctionBased" ;
    agentoscin:hasValidationLogic  "check_bullet_count" ;
    agentoscin:hasMaxRetries       2 .
```

---

## 3. Tool Mapping

### Ontology anchor

- Class: `agentoscin:Tool`
- Datatype: `hasTitle`, `hasDescription`, `hasInputSchema`, `hasImplementationReference`

### Triple table

| Source concept | Subject | Predicate | Object |
|---|---|---|---|
| tool exists | `:Tool_<class>` | `rdf:type` | `agentoscin:Tool` |
| name | `:Tool_<class>` | `agentoscin:hasTitle` | `"<tool_name>"` |
| description | `:Tool_<class>` | `agentoscin:hasDescription` | `"<docstring>"` |
| input schema | `:Tool_<class>` | `agentoscin:hasInputSchema` | `"<JSON Schema>"` |
| impl ref | `:Tool_<class>` | `agentoscin:hasImplementationReference` | `"<module>.<func>"` |

### Framework source — manual mapping

| Source snippet | Manual TTL |
|---|---|
| **CrewAI BaseTool**<br>`class SearchTool(BaseTool):`<br>`  name = "Search"`<br>`  description = "Search the web."`<br>`  args_schema = SearchArgs`<br>`  def _run(self, query: str) -> str: …` | `:Tool_SearchTool a agentoscin:Tool ; agentoscin:hasTitle "Search" ; agentoscin:hasDescription "Search the web." ; agentoscin:hasInputSchema "{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\"}},\"required\":[\"query\"]}" ; agentoscin:hasImplementationReference "tools.SearchTool" .` |
| **LangGraph `@tool`**<br>`@tool`<br>`def web_search(query: str) -> str:`<br>`  """Search the web."""` | `:Tool_web_search a agentoscin:Tool ; agentoscin:hasTitle "web_search" ; agentoscin:hasDescription "Search the web." ; agentoscin:hasInputSchema "{\"properties\":{\"query\":{\"type\":\"string\"}},\"required\":[\"query\"],\"type\":\"object\"}" ; agentoscin:hasImplementationReference "tools.web_search" .` |
| **AutoGen `FunctionTool`**<br>`def add(a: int, b: int) -> int: …`<br>`add_tool = FunctionTool(add, description="Adds two numbers")` | `:Tool_add a agentoscin:Tool ; agentoscin:hasTitle "add" ; agentoscin:hasDescription "Adds two numbers" ; agentoscin:hasInputSchema "{\"properties\":{\"a\":{\"type\":\"integer\"},\"b\":{\"type\":\"integer\"}},\"required\":[\"a\",\"b\"],\"type\":\"object\"}" ; agentoscin:hasImplementationReference "tools.add" .` |

---

## 4. Team Mapping

### Ontology anchor

- Class: `agentoscin:Team` (parent of `Orchestration`)
- Outgoing: `hasAgentMember`, `employsCoordinationPattern`, `hasWorkflowPattern`, `hasTerminationCondition`, `hasTeamMemoryBinding`
- Datatype: `hasTitle`

### Triple table

| Source concept | Subject | Predicate | Object |
|---|---|---|---|
| team exists | `:Team_<name>` | `rdf:type` | `agentoscin:Team` |
| title | `:Team_<name>` | `agentoscin:hasTitle` | `"<class_name>"` |
| member | `:Team_<name>` | `agentoscin:hasAgentMember` | `:Agent_<k>` |
| coordination | `:Team_<name>` | `agentoscin:employsCoordinationPattern` | one of `agentoscin:Sequential`/`Hierarchical`/`RoundRobin`/`SelectorBased`/`Swarm`/`ReActLoop`/`Network`/`Custom` |
| termination | `:Team_<name>` | `agentoscin:hasTerminationCondition` | termination individual |
| workflow | `:Team_<name>` | `agentoscin:hasWorkflowPattern` | `:WorkflowPattern_<name>` |

### Framework mapping table

| Source | Coordination pattern | Default termination |
|---|---|---|
| **CrewAI** `Crew(..., process=Process.sequential)` | `:Sequential` | `TaskCompletionTermination` |
| **CrewAI** `Crew(..., process=Process.hierarchical)` | `:Hierarchical` | `TaskCompletionTermination` |
| **LangGraph** linear `.add_edge(a, b)` chain | `:Sequential` | `RoutingTermination` (via `END`) |
| **LangGraph** `create_react_agent(...)` | `:ReActLoop` | `RoutingTermination` |
| **LangGraph** conditional edges / supervisor pattern | `:Hierarchical` | `RoutingTermination` |
| **LangGraph** otherwise | `:Custom` | `RoutingTermination` |
| **AutoGen** `RoundRobinGroupChat` | `:RoundRobin` | depends on `termination_condition` kwarg |
| **AutoGen** `SelectorGroupChat` | `:SelectorBased` | depends on `termination_condition` kwarg |
| **AutoGen** `Swarm` | `:Swarm` | depends on `termination_condition` kwarg |
| **AutoGen** `MagenticOneGroupChat` | `:Custom` | depends on `termination_condition` kwarg |

### Concrete worked example (CrewAI Crew)

**Source**:
```python
@crew
def crew(self) -> Crew:
    return Crew(
        agents=[self.researcher(), self.writer()],
        tasks=[self.research(), self.write()],
        process=Process.sequential,
        verbose=True,
        memory=True,
    )
```

**Manual TTL**:
```turtle
:Team_ContentCrew a agentoscin:Team ;
    agentoscin:hasTitle                  "ContentCrew" ;
    agentoscin:hasAgentMember            :Agent_researcher , :Agent_writer ;
    agentoscin:employsCoordinationPattern agentoscin:Sequential ;
    agentoscin:hasTerminationCondition   :Termination_ContentCrew ;
    agentoscin:hasWorkflowPattern        :WorkflowPattern_ContentCrew ;
    agentoscin:hasSystemConfig           :Config_verbose_Team_ContentCrew ;
    agentoscin:hasTeamMemoryBinding      :MemoryBinding_GroupShared_ContentCrew .

:Termination_ContentCrew a agentoscin:TaskCompletionTermination .

:WorkflowPattern_ContentCrew a agentoscin:WorkflowPattern ;
    agentoscin:hasWorkflowStep :CrewStep_ContentCrew_research ,
                               :CrewStep_ContentCrew_write .

:CrewStep_ContentCrew_research a agentoscin:StartStep ;
    agentoscin:hasTitle            "research" ;
    agentoscin:stepOrder           1 ;
    agentoscin:hasAssociatedTask   :Task_research ;
    agentoscin:nextStep            :CrewStep_ContentCrew_write .

:CrewStep_ContentCrew_write a agentoscin:EndStep ;
    agentoscin:hasTitle            "write" ;
    agentoscin:stepOrder           2 ;
    agentoscin:hasAssociatedTask   :Task_write .
```

---

## 5. Termination Mapping (AutoGen focus)

### Ontology anchor

- `TerminationCondition` (parent)
  - `TurnLimitTermination` — `hasMaxTurns` (xsd:integer)
  - `EventBasedTermination` — `hasTriggerExpression` (xsd:string)
  - `RoutingTermination`
  - `TaskCompletionTermination`
  - `CompositeTermination` — `hasOperator` ("OR"/"AND") + `hasSubCondition`

### Mapping table

| Source construct | RDF type | Extra properties |
|---|---|---|
| `MaxMessageTermination(N)` | `TurnLimitTermination` | `hasMaxTurns N` |
| `TextMentionTermination("X")` | `EventBasedTermination` | `hasTriggerExpression "X"` |
| `HandoffTermination(...)` | `EventBasedTermination` | `hasTriggerExpression "HandoffTermination"` |
| `ExternalTermination(...)` | `EventBasedTermination` | `hasTriggerExpression "ExternalTermination"` |
| `a \| b` (BinOp) | `CompositeTermination` | `hasOperator "OR"` + `hasSubCondition` ×2 |
| `a & b` (BinOp) | `CompositeTermination` | `hasOperator "AND"` + `hasSubCondition` ×2 |
| implicit (CrewAI default) | `TaskCompletionTermination` | — |
| implicit (LangGraph default) | `RoutingTermination` | — |

### Concrete worked example (AutoGen composite)

**Source**:
```python
max_msg = MaxMessageTermination(10)
on_approve = TextMentionTermination("APPROVE")
termination = max_msg | on_approve

team = RoundRobinGroupChat(
    participants=[agent_a, agent_b],
    termination_condition=termination,
)
```

**Manual TTL**:
```turtle
:Team_chat a agentoscin:Team ;
    agentoscin:hasAgentMember            :Agent_agent_a , :Agent_agent_b ;
    agentoscin:employsCoordinationPattern agentoscin:RoundRobin ;
    agentoscin:hasTerminationCondition   :Composite_chat_0 .

:Composite_chat_0 a agentoscin:CompositeTermination ;
    agentoscin:hasOperator     "OR" ;
    agentoscin:hasSubCondition :TurnLimit_chat_0_sub0 ,
                               :EventTermination_chat_0_sub1 .

:TurnLimit_chat_0_sub0 a agentoscin:TurnLimitTermination ;
    agentoscin:hasMaxTurns 10 .

:EventTermination_chat_0_sub1 a agentoscin:EventBasedTermination ;
    agentoscin:hasTriggerExpression "APPROVE" .
```

---

## 6. Flow / Orchestration Mapping

### Ontology anchor

- Class: `agentoscin:Orchestration` (subclass of Team)
- Outgoing: `orchestratesTeam`, `hasWorkflowPattern`
- Workflow steps: `WorkflowStep` subtypes — `StartStep`, `EndStep`, `ConditionalStep`
- Datatype on steps: `hasTitle`, `stepOrder`, `hasRoutingLogic`, `hasEdgeMapping`, `hasDecoratorArgument`
- Edges: `nextStep`

### Mapping table

| Source construct | Step RDF type | Notable properties |
|---|---|---|
| **CrewAI** `@start(...)` / `@start("label")` | `StartStep` (+ `WorkflowStep`) | `hasDecoratorArgument` if non-method arg |
| **CrewAI** `@listen(source)` | `WorkflowStep` | `nextStep` edge from source |
| **CrewAI** `@router(source)` | `ConditionalStep` | `hasRoutingLogic` = function body; outgoing `nextStep` per return value |
| **LangGraph** `.add_node("x", fn)` | `WorkflowStep` | |
| **LangGraph** `.add_edge("a", "b")` | (edge) | `:FlowStep_a agentoscin:nextStep :FlowStep_b` |
| **LangGraph** `.add_conditional_edges("a", fn, {"yes": "b", "no": "c"})` | a → `ConditionalStep` | `hasRoutingLogic` = `fn.__body__`; `hasEdgeMapping` = `{"yes":"b","no":"c"}` |
| dead-end step (no outgoing edges) | additionally `EndStep` | — |

### Concrete worked example (CrewAI Flow)

**Source**:
```python
class ContentFlow(Flow):
    @start()
    def kickoff(self):
        return self.state.topic

    @listen(kickoff)
    def research(self, topic):
        return ContentCrew().crew().kickoff(inputs={"topic": topic})

    @router(research)
    def route(self, result):
        return "publish" if result.score > 0.8 else "revise"

    @listen("publish")
    def publish(self, _):
        ...

    @listen("revise")
    def revise(self, _):
        ...
```

**Manual TTL**:
```turtle
:Orchestration_ContentFlow a agentoscin:Orchestration ;
    agentoscin:hasTitle                  "ContentFlow" ;
    agentoscin:orchestratesTeam          :Team_ContentCrew ;
    agentoscin:employsCoordinationPattern agentoscin:Custom ;
    agentoscin:hasWorkflowPattern        :FlowWorkflowPattern_ContentFlow .

:FlowWorkflowPattern_ContentFlow a agentoscin:WorkflowPattern ;
    agentoscin:hasWorkflowStep :FlowStep_kickoff , :FlowStep_research ,
                               :FlowStep_route , :FlowStep_publish ,
                               :FlowStep_revise .

:FlowStep_kickoff a agentoscin:StartStep ;
    agentoscin:hasTitle  "kickoff" ;
    agentoscin:stepOrder 1 ;
    agentoscin:nextStep  :FlowStep_research .

:FlowStep_research a agentoscin:WorkflowStep ;
    agentoscin:hasTitle  "research" ;
    agentoscin:stepOrder 2 ;
    agentoscin:nextStep  :FlowStep_route .

:FlowStep_route a agentoscin:ConditionalStep ;
    agentoscin:hasTitle        "route" ;
    agentoscin:stepOrder       3 ;
    agentoscin:hasRoutingLogic "return \"publish\" if result.score > 0.8 else \"revise\"" ;
    agentoscin:nextStep        :FlowStep_publish , :FlowStep_revise .

:FlowStep_publish a agentoscin:WorkflowStep, agentoscin:EndStep ;
    agentoscin:hasTitle  "publish" ;
    agentoscin:stepOrder 4 .

:FlowStep_revise a agentoscin:WorkflowStep, agentoscin:EndStep ;
    agentoscin:hasTitle  "revise" ;
    agentoscin:stepOrder 5 .
```

### Concrete worked example (LangGraph conditional edges)

**Source**:
```python
graph = StateGraph(State)
graph.add_node("plan", plan_fn)
graph.add_node("execute", execute_fn)
graph.add_edge(START, "plan")
graph.add_conditional_edges("plan", decide, {"go": "execute", "stop": END})
graph.add_edge("execute", END)
```

**Manual TTL** (relevant fragment):
```turtle
:FlowStep_plan a agentoscin:ConditionalStep ;
    agentoscin:hasTitle        "plan" ;
    agentoscin:stepOrder       1 ;
    agentoscin:hasRoutingLogic "<decide function body>" ;
    agentoscin:hasEdgeMapping  "{\"go\":\"execute\",\"stop\":\"END\"}" ;
    agentoscin:nextStep        :FlowStep_execute .

:FlowStep_execute a agentoscin:WorkflowStep, agentoscin:EndStep ;
    agentoscin:hasTitle  "execute" ;
    agentoscin:stepOrder 2 .
```

---

## 7. Memory Mapping

### Ontology anchor

- `MemoryBinding` (with `hasMemoryScope`, `bindsMemory`)
- `Memory` (with `hasPersistenceScope`, `hasTitle`)

### Mapping table

| Source construct | Scope | Persistence | Memory title |
|---|---|---|---|
| **CrewAI** `Agent(..., memory=True)` | `AgentPrivate` | `Persistent` | — |
| **CrewAI** `Crew(..., memory=True)` | `GroupShared` | `Persistent` | — |
| **LangGraph** `MemorySaver()` + `compile(checkpointer=…)` | `GroupShared` | `ExecutionScoped` | `"MemorySaver"` |
| **AutoGen** `AssistantAgent(..., memory=[ListMemory()])` | `AgentPrivate` | `ExecutionScoped` | `"ListMemory"` |
| **AutoGen** `AssistantAgent(..., memory=[ChromaDBVectorMemory(...)])` | `AgentPrivate` | `Persistent` | `"ChromaDBVectorMemory"` |

### Triple pattern

```turtle
:Agent_<k> agentoscin:hasMemoryBinding :MemoryBinding_<scope>_<k> .
:MemoryBinding_<scope>_<k> a agentoscin:MemoryBinding ;
    agentoscin:hasMemoryScope "<scope>" ;
    agentoscin:bindsMemory    :Memory_<scope>_<k> .
:Memory_<scope>_<k> a agentoscin:Memory ;
    agentoscin:hasPersistenceScope "<persistence>" ;
    agentoscin:hasTitle            "<backend class>" .
```

---

## 8. Guardrail Mapping (CrewAI-only)

### Ontology anchor

- `Guardrail` (with `hasGuardrailType`, `hasValidationLogic`, `hasMaxRetries`, `hasDescription`)

### Mapping table

| Source construct | `hasGuardrailType` | Detail slot | Detail content |
|---|---|---|---|
| `Task(guardrail=my_func)` | `"FunctionBased"` | `hasValidationLogic` | `"my_func"` (function name) |
| `Task(guardrail="Check that output …")` | `"LLMBased"` | `hasDescription` | the literal prompt |
| `Task(guardrail=<non-callable, non-string>)` | *(absent)* | `hasDescription` | stringified fallback |
| `guardrail_max_retries=N` *(on Task, applies to all its guardrails)* | — | `hasMaxRetries` | `N` (xsd:integer) |

---

## 9. System-Level Mapping

### Ontology anchor

- `agentoscin:AgenticSystem`
- Outgoing: `containsAgent`, `containsTeam`, `containsOrchestration`
- Datatype: `hasTitle`, `hasSourceFramework`

### Triple table

| Source concept | Subject | Predicate | Object |
|---|---|---|---|
| system exists | `:<system_name>` | `rdf:type` | `agentoscin:AgenticSystem` |
| system title | `:<system_name>` | `agentoscin:hasTitle` | `"<system_name>"` |
| originating framework | `:<system_name>` | `agentoscin:hasSourceFramework` | `"CrewAI" \| "LangGraph" \| "AutoGen_v0.4"` |
| all agents | `:<system_name>` | `agentoscin:containsAgent` | each `:Agent_<k>` |
| all teams | `:<system_name>` | `agentoscin:containsTeam` | each `:Team_<t>` |
| flow | `:<system_name>` | `agentoscin:containsOrchestration` | `:Orchestration_<class>` |

### Example

```turtle
:tech_blog a agentoscin:AgenticSystem ;
    agentoscin:hasTitle           "tech_blog" ;
    agentoscin:hasSourceFramework "CrewAI" ;
    agentoscin:containsAgent      :Agent_researcher , :Agent_writer , :Agent_editor ;
    agentoscin:containsTeam       :Team_ContentCrew ;
    agentoscin:containsOrchestration :Orchestration_ContentFlow .
```

---

## 10. End-to-End Minimal Example (CrewAI → TTL)

**Source** (single file, stripped to essentials):

```python
class ResearchCrew:
    @agent
    def researcher(self) -> Agent:
        return Agent(
            role="Researcher",
            goal="Find facts about the topic",
            backstory="Expert researcher",
            llm="gpt-4o",
        )

    @task
    def research(self) -> Task:
        return Task(
            description="Research the topic thoroughly.",
            expected_output="A list of 5 sources.",
            agent=self.researcher(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.researcher()],
            tasks=[self.research()],
            process=Process.sequential,
        )
```

**Complete manual TTL**:

```turtle
@prefix :           <http://example.org/research_system#> .
@prefix agentoscin: <http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/> .
@prefix rdf:        <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd:        <http://www.w3.org/2001/XMLSchema#> .

# ---- Agent ----
:Agent_researcher a agentoscin:LLMAgent ;
    agentoscin:agentID             "researcher" ;
    agentoscin:agentRole           "Researcher" ;
    agentoscin:agentType           "GeneralPurpose" ;
    agentoscin:hasReasoningEnabled false ;
    agentoscin:hasAgentGoal        :Goal_researcher ;
    agentoscin:agentPrompt         :AgentPrompt_researcher ;
    agentoscin:useLanguageModel    :LM_gpt_4o .

:Goal_researcher a agentoscin:Goal ;
    agentoscin:hasDescription "Find facts about the topic" .

:AgentPrompt_researcher a agentoscin:Prompt ;
    agentoscin:promptInstruction    "Researcher: Find facts about the topic" ;
    agentoscin:promptContext        "Expert researcher" ;
    agentoscin:hasDirectiveFunction "DualDirective" ;
    agentoscin:hasSourceAttribute   "role, goal, backstory" .

:LM_gpt_4o a agentoscin:LanguageModel ;
    agentoscin:hasTitle "gpt-4o" .

# ---- Task ----
:Task_research a agentoscin:Task ;
    agentoscin:hasExpectedOutput     "A list of 5 sources." ;
    agentoscin:performedByAgent      :Agent_researcher ;
    agentoscin:hasDelegationStrategy "ExplicitAssignment" ;
    agentoscin:taskPrompt            :TaskPrompt_research .

:TaskPrompt_research a agentoscin:Prompt ;
    agentoscin:promptInstruction     "Research the topic thoroughly." ;
    agentoscin:promptOutputIndicator "A list of 5 sources." ;
    agentoscin:hasSourceAttribute    "description, expected_output" .

# ---- Team ----
:Team_ResearchCrew a agentoscin:Team ;
    agentoscin:hasTitle                   "ResearchCrew" ;
    agentoscin:hasAgentMember             :Agent_researcher ;
    agentoscin:employsCoordinationPattern agentoscin:Sequential ;
    agentoscin:hasTerminationCondition    :Termination_ResearchCrew ;
    agentoscin:hasWorkflowPattern         :WorkflowPattern_ResearchCrew .

:Termination_ResearchCrew a agentoscin:TaskCompletionTermination .

:WorkflowPattern_ResearchCrew a agentoscin:WorkflowPattern ;
    agentoscin:hasWorkflowStep :CrewStep_ResearchCrew_research .

:CrewStep_ResearchCrew_research a agentoscin:StartStep, agentoscin:EndStep ;
    agentoscin:hasTitle          "research" ;
    agentoscin:stepOrder         1 ;
    agentoscin:hasAssociatedTask :Task_research .

# ---- System ----
:research_system a agentoscin:AgenticSystem ;
    agentoscin:hasTitle           "research_system" ;
    agentoscin:hasSourceFramework "CrewAI" ;
    agentoscin:containsAgent      :Agent_researcher ;
    agentoscin:containsTeam       :Team_ResearchCrew .
```

---

## 11. Property Coverage Matrix

Rows = ontology property. Columns = which framework's source actually carries
the information needed to populate that property.

| Property | CrewAI | LangGraph | AutoGen |
|---|:-:|:-:|:-:|
| `agentID` | ✓ | ✓ | ✓ |
| `agentRole` | ✓ | ✓ (node name) | ✓ |
| `agentType` | — (always `GeneralPurpose`) | — | ✓ (distinguishes `UserProxy`) |
| `hasReasoningEnabled` | ✓ | ✓ (from `create_react_agent`) | — |
| `hasReasoningOrigin` | — | ✓ | — |
| `employsReasoningPattern` → `ReAct` | — | ✓ | — |
| `hasAgentGoal` | ✓ | — | — |
| `agentPrompt` | ✓ (`DualDirective`) | — | ✓ (`ModelDirective`) |
| `agentToolUsage` | ✓ | ✓ | ✓ |
| `useLanguageModel` | ✓ | ✓ | ✓ |
| `hasAgentConfig` (verbose, allow_delegation) | ✓ | — | — |
| `hasMemoryBinding` | ✓ | ✓ (checkpointer) | ✓ (memory=) |
| `hasKnowledge` | ✓ | — | — |
| `hasHumanCheckpoint` | ✓ (`human_input=True`) | ✓ (interrupt_before) | ✓ (`UserProxyAgent`) |
| `performedByAgent` | ✓ | ✓ (1:1 node↔agent) | — (orchestrator-delegated) |
| `hasExpectedOutput` | ✓ | — | — |
| `hasOutputSchema` | ✓ (`output_pydantic`) | ✓ (`state_fields`) | — |
| `dependsOn` | ✓ (`context=`) | ✓ (edges) | — |
| `hasGuardrail` | ✓ | — | — |
| `hasMaxRetries` | ✓ (`guardrail_max_retries`) | — | — |
| `employsCoordinationPattern` | ✓ (from `Process`) | ✓ (inferred) | ✓ (from GroupChat class) |
| `hasTerminationCondition` → `TaskCompletionTermination` | ✓ (implicit) | — | — |
| `hasTerminationCondition` → `RoutingTermination` | — | ✓ (END node) | — |
| `hasTerminationCondition` → `TurnLimitTermination` | — | — | ✓ (`MaxMessageTermination`) |
| `hasTerminationCondition` → `EventBasedTermination` | — | — | ✓ (`TextMentionTermination`) |
| `hasTerminationCondition` → `CompositeTermination` | — | — | ✓ (`a \| b`, `a & b`) |
| `hasWorkflowPattern` | ✓ | ✓ | ✓ |
| `hasRoutingLogic` | ✓ (`@router` body) | ✓ (conditional-edges fn) | — |
| `hasEdgeMapping` | — | ✓ | — |
| `hasDecoratorArgument` | ✓ (`@listen("label")`) | — | — |
| `orchestratesTeam` | ✓ (`@crew` invocations in Flow) | — | — |
| `containsOrchestration` | ✓ (Flow class) | ✓ (StateGraph) | ✓ (`run_stream(task=...)`) |
| `hasSourceFramework` | `"CrewAI"` | `"LangGraph"` | `"AutoGen_v0.4"` |

A `—` means the framework does not surface that information in source code, so
the corresponding triple is either absent or emitted with a default value.

---

## Appendix A — Decision trees

### A.1. Which `agentType` to emit?

```
if class == UserProxyAgent or accepts user input → "UserProxy"
elif created via manager_llm / manager_agent kwarg → "Manager"
else                                              → "GeneralPurpose"
```

### A.2. Which `hasDelegationStrategy` to emit?

```
if task.agent is set         → "ExplicitAssignment"
elif team topology decides   → "TopologyDetermined"   (LangGraph)
else                         → "OrchestratorDelegated" (AutoGen run_stream, hierarchical manager)
```

### A.3. Which termination class for a CrewAI team?

```
if team.max_turns           → TurnLimitTermination + hasMaxTurns
else                        → TaskCompletionTermination (default)
```

### A.4. Which coordination pattern for a LangGraph graph?

```
if any agent built via create_react_agent                → ReActLoop
elif conditional edges form hub-and-spoke (supervisor)   → Hierarchical
elif edges form a linear chain                           → Sequential
else                                                     → Custom
```

### A.5. Which RDF type for a CrewAI flow step?

```
decorator → step type
@start(...)      → StartStep (+ WorkflowStep)
@router(...)     → ConditionalStep
@listen(x)       → WorkflowStep
no outgoing edge → additionally EndStep
```

---

## Appendix B — Literal encoding

- Strings: `xsd:string`, with `\\` → `\\\\`, `"` → `\\"`, newline → `\\n`.
- Integers: `xsd:integer`, plain digits.
- Booleans: `xsd:boolean`, `true` / `false` (lowercase).
- JSON literals (schemas, edge mappings): canonicalised via
  `json.dumps(..., sort_keys=True)` so that semantically identical dicts
  produce byte-identical literals. Separators `","`, `":"` for compactness.
- Function bodies (in `hasRoutingLogic`): the Python source fragment, dedented,
  stored as a single `xsd:string`.

---

## Appendix C — What the mapping *does not* capture

By design, these source-level details are not round-tripped:

- Python import statements and module layout (regenerated by generators).
- Arbitrary keyword arguments on Agent/Task/Crew that don't correspond to
  an ontology property (e.g. CrewAI's `max_iter`, `max_execution_time`).
- Decorator order and method body statements outside of `@router`.
- Comments and docstrings other than tool/node descriptions.
- The exact LLM client wiring (model client instances); only the model name
  is preserved via `hasTitle` on `LanguageModel`.
- Async/sync distinction of tool functions.

These omissions are intentional: the ontology captures the **semantic
architecture** of an agentic system, not its runtime configuration.
