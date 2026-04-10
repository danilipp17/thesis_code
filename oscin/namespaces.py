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
# Convenience URIRefs for properties that contain colons in their
# local names.  RDFLib's Namespace.__getattr__ cannot handle colons,
# so we construct these manually.
# ---------------------------------------------------------------------------
DCTERMS_TITLE = URIRef(
    "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/dcterms:title"
)
DCTERMS_DESCRIPTION = URIRef(
    "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/dcterms:description"
)
DCTERMS_REFERENCE = URIRef(
    "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/dcterms:reference"
)

# ---------------------------------------------------------------------------
# Coordination pattern named individuals (pre-defined in the ontology)
# ---------------------------------------------------------------------------
COORD_SEQUENTIAL = AGENTOSCIN["Sequentiel"]    # as spelled in the ontology
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
