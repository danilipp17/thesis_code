"""
namespaces.py
=============
Central namespace definitions for the OSCIN extraction pipeline.

agentoscin extends agentO and reuses BEAM/PROV/p-plan upstream
ontologies. Each imported vocabulary gets its own ``rdflib.Namespace``
so emission sites can use the canonical IRI for each term instead of
re-minting it under the agentoscin namespace.

The instance namespace is parameterised at runtime to allow different
instance namespaces per extraction run.
"""

from rdflib import Namespace

# ---------------------------------------------------------------------------
# Ontology vocabulary namespaces
# ---------------------------------------------------------------------------
AGENTOSCIN = Namespace(
    "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
)
AGENTO = Namespace("http://www.w3id.org/agentic-ai/onto#")
BEAM = Namespace("http://w3id.org/beam/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")
PPLAN = Namespace("http://purl.org/net/p-plan#")

# Set of all ontology-vocabulary namespaces (for filters that need to
# distinguish T-Box / vocabulary URIs from A-Box instance URIs).
ONTOLOGY_NAMESPACES = (
    str(AGENTOSCIN),
    str(AGENTO),
    str(BEAM),
    str(PROV),
    str(PPLAN),
)


def is_ontology_uri(uri: str) -> bool:
    """Return True iff ``uri`` lives in any of the imported ontologies.

    Each namespace constant ends with a trailing separator (``/`` or ``#``),
    but the ontology *root IRI* itself — e.g. the one used in ``owl:imports``
    statements — does not. Both forms must be recognised, otherwise the
    ontology-level metadata triples
    (``owl:imports``, ``dc:title``, ``dc:creator`` …) leak into ABox
    comparisons.
    """
    s = str(uri)
    for ns in ONTOLOGY_NAMESPACES:
        if s.startswith(ns) or s == ns.rstrip("/#"):
            return True
    return False


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
