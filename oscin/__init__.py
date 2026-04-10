"""
OSCIN — Ontology-driven Source Code Interoperability
=====================================================

Multi-framework extraction pipeline for populating an agentic AI
ontology from framework-specific source code.

Supported frameworks:
  - CrewAI   (crewai_parser)
  - AutoGen  (autogen_parser)
  - LangGraph (langgraph_parser)

Architecture:
  Layer 1 — Framework-specific parsers produce intermediate representations
  Layer 2 — Shared dataclasses (intermediate.py) serve as the contract
  Layer 3 — A single OntologyPopulator maps intermediates to RDF/OWL

Author:  Dani Lippmann
Context: Master Thesis — Towards Interoperability between Agentic AI
         Frameworks through Semantic Representation
Date:    April 2026
"""

__version__ = "0.1.0"
