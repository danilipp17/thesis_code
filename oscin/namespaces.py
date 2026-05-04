"""
namespaces.py
=============
Central namespace definitions for the OSCIN extraction pipeline.

The AGENTOSCIN namespace points to the ontology vocabulary defined
in the thesis (agentoscin.ttl).  The instance namespace is
parameterised at runtime to allow different instance namespaces
per extraction run.
"""

from rdflib import Namespace, URIRef

# ---------------------------------------------------------------------------
# Ontology vocabulary namespace (fixed — same for all extractions)
# ---------------------------------------------------------------------------
AGENTOSCIN = Namespace(
    "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
)

# ---------------------------------------------------------------------------
# Convenience aliases for commonly used data properties
# ---------------------------------------------------------------------------
HAS_TITLE = AGENTOSCIN.hasTitle
HAS_DESCRIPTION = AGENTOSCIN.hasDescription
HAS_REFERENCE = AGENTOSCIN.hasReference
CALLS_CREW = AGENTOSCIN.callsCrew

# ---------------------------------------------------------------------------
# Coordination pattern named individuals (pre-defined in the ontology)
# ---------------------------------------------------------------------------
COORD_SEQUENTIAL = AGENTOSCIN["Sequential"]
COORD_HIERARCHICAL = AGENTOSCIN["Hierarchical"]
COORD_ROUND_ROBIN = AGENTOSCIN["RoundRobin"]
COORD_SELECTOR_BASED = AGENTOSCIN["SelectorBased"]
COORD_SWARM = AGENTOSCIN["Swarm"]
COORD_REACT_LOOP = AGENTOSCIN["ReActLoop"]
COORD_NETWORK = AGENTOSCIN["Network"]
COORD_CUSTOM = AGENTOSCIN["Custom"]


def make_instance_namespace(uri: str) -> Namespace:
    """
    Create an RDFLib Namespace for instance individuals.

    Parameters
    ----------
    uri : str
        The base URI for the instance namespace.  Must end with ``#``
        or ``/`` so that RDFLib can append local names correctly.

    Returns
    -------
    Namespace
        An RDFLib Namespace bound to *uri*.
    """
    if not uri.endswith(("#", "/")):
        uri += "#"
    return Namespace(uri)
