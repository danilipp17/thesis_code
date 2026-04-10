"""
intermediate.py
================
Shared Intermediate Representation for the OSCIN extraction pipeline.

These dataclasses form the contract between framework-specific parsers
(Layer 1) and the shared ontology populator (Layer 3).  Every parser
— regardless of source framework — must produce instances of these
classes.  The populator consumes them without knowing which framework
they originated from.

Each field is annotated with the ontology property it maps to,
referencing the CrewAI → Ontology Mapping Table section numbers from
the thesis.

Design rationale
----------------
The field names intentionally mirror *ontology concepts* (e.g. ``role``,
``goal``, ``backstory``) rather than framework-specific terminology.
Where a framework uses different wording (e.g. AutoGen's
``system_message`` instead of ``backstory``), the parser is responsible
for mapping into this shared vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ===================================================================
# Agent
# ===================================================================

@dataclass
class ExtractedAgent:
    """
    Intermediate representation of an agent from any framework.

    Mapping table: Section 1 (Agent Mapping).
    """
    # Identity
    agent_key: str              # Unique key within the extraction run
    role: str                   # → agentID, agentRole
    goal: str                   # → hasAgentGoal
    backstory: str              # → agentPrompt.promptContext

    # Optional parameters
    llm: Optional[str] = None               # → useLanguageModel
    tools: list[str] = field(default_factory=list)  # → agentToolUsage
    reasoning: bool = False                  # → hasReasoningEnabled
    max_reasoning_attempts: Optional[int] = None  # → hasMaxReasoningAttempts
    memory: bool = False                     # → hasMemoryBinding
    verbose: Optional[bool] = None           # → hasAgentConfig
    allow_delegation: Optional[bool] = None  # → hasAgentConfig

    # Provenance
    source_file: str = ""


# ===================================================================
# Task
# ===================================================================

@dataclass
class ExtractedTask:
    """
    Intermediate representation of a task from any framework.

    Mapping table: Section 2 (Task Mapping).
    """
    task_key: str               # Unique key within the extraction run
    description: str            # → taskPrompt.promptInstruction
    expected_output: str        # → hasExpectedOutput
    agent_key: Optional[str] = None  # → performedByAgent

    # Optional parameters
    output_pydantic: Optional[str] = None    # Class name → hasOutputSchema
    output_json: Optional[str] = None        # → hasOutputSchema
    tools: list[str] = field(default_factory=list)  # → taskToolUsage
    context_tasks: list[str] = field(default_factory=list)  # → dependsOn
    human_input: bool = False                # → hasHumanCheckpoint
    guardrails: list[str] = field(default_factory=list)  # → hasGuardrail

    # Provenance
    source_file: str = ""


# ===================================================================
# Tool
# ===================================================================

@dataclass
class ExtractedTool:
    """
    Intermediate representation of a tool from any framework.

    Mapping table: Section 5 (Tool Mapping).
    """
    class_name: str             # Python class name
    name: str                   # → dcterms:title
    description: str            # → dcterms:description
    args_schema_json: str       # Serialized JSON Schema → hasInputSchema
    implementation_ref: str     # Module path → hasImplementationReference
    source_file: str = ""


# ===================================================================
# Team (was "Crew" in the CrewAI-only extractor)
# ===================================================================

@dataclass
class ExtractedTeam:
    """
    Intermediate representation of a team / group of agents.

    Mapping table: Section 3 (Crew/Team Mapping).

    This was previously named ``ExtractedCrew``; renamed to use the
    ontology term so that the intermediate layer is framework-neutral.
    """
    team_class_name: str        # Python class name → dcterms:title
    agent_keys: list[str]       # References to agents → hasAgentMember
    task_keys: list[str]        # References to tasks → workflow steps
    process: str = "sequential" # "sequential" or "hierarchical"
    verbose: bool = False       # → hasSystemConfig
    memory: bool = False        # → hasTeamMemoryBinding
    manager_llm: Optional[str] = None       # → Manager agent
    manager_agent: Optional[str] = None     # → Manager agent
    source_file: str = ""


# ===================================================================
# Flow / Orchestration
# ===================================================================

@dataclass
class ExtractedFlowStep:
    """
    Intermediate representation of a single orchestration step.

    Mapping table: Section 4 (Flow Mapping).
    """
    method_name: str            # Python method / node name → step title
    decorator_type: str         # "start", "listen", or "router"
    decorator_args: list[str]   # Arguments to the decorator / edge targets
    calls_crew: Optional[str] = None   # If step invokes a team
    return_values: list[str] = field(default_factory=list)  # Router returns
    function_body: str = ""     # Serialized body → hasRoutingLogic (routers)


@dataclass
class ExtractedFlow:
    """
    Intermediate representation of an orchestration flow.

    Mapping table: Section 4 (Flow Mapping).
    """
    class_name: str             # Python class / graph name → dcterms:title
    state_model: Optional[str] = None  # State schema name
    steps: list[ExtractedFlowStep] = field(default_factory=list)
    crew_references: list[str] = field(default_factory=list)
    source_file: str = ""


# ===================================================================
# Pydantic / Structured-Output Model
# ===================================================================

@dataclass
class ExtractedPydanticModel:
    """
    Intermediate representation of a Pydantic BaseModel used for
    structured output (e.g. Task.output_pydantic).
    """
    class_name: str
    fields: dict[str, dict[str, str] | str]  # field_name → type info
    source_file: str = ""
