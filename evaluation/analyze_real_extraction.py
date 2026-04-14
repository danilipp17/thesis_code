import glob
from rdflib import Graph, Namespace, URIRef
from collections import defaultdict

ontology_file = "ontology/agentoscin.ttl"

# ONLY look at naturally extracted files
generated_files = [
    "output/custom_extracted/autogen.ttl",
    "output/custom_extracted/langgraph.ttl",
    "output/custom_extracted/crewai.ttl",
    "output/langgraph_test/research.ttl",
    "output/crewai/academic_flow.ttl",
]

AGENTOSCIN = Namespace(
    "http://www.semanticweb.org/danilippmann/ontologies/2026/3/agentoscin/"
)

# 1. Parse Ontology to get all classes and properties
onto = Graph()
onto.parse(ontology_file, format="turtle")

OWL = Namespace("http://www.w3.org/2002/07/owl#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

classes = set(s for s in onto.subjects(RDF.type, OWL.Class))
object_props = set(s for s in onto.subjects(RDF.type, OWL.ObjectProperty))
data_props = set(s for s in onto.subjects(RDF.type, OWL.DatatypeProperty))

usage = {
    "classes": {c: 0 for c in classes if str(c).startswith(AGENTOSCIN)},
    "object_props": {p: 0 for p in object_props if str(p).startswith(AGENTOSCIN)},
    "data_props": {p: 0 for p in data_props if str(p).startswith(AGENTOSCIN)},
}

# 2. Parse extracted files and count INSTANCES and PREDICATES
for filepath in generated_files:
    try:
        g = Graph()
        g.parse(filepath, format="turtle")

        # Count Class usages (Instances of a class)
        for c in usage["classes"]:
            # Find how many subjects have this class as their type
            instances = list(g.subjects(RDF.type, c))
            # Subtract 1 if the ontology definition is in the graph (i.e. 'c a owl:Class')
            # Wait, g.subjects(RDF.type, c) finds ?s a c. The definition is c a owl:Class.
            # So this ONLY counts actual instances!
            usage["classes"][c] += len(instances)

        # Count Property usages (Used as predicates)
        for p in usage["object_props"]:
            triples = list(g.triples((None, p, None)))
            # Exclude ontology definition lines like `p rdfs:domain X` which is not a usage of `p` as a predicate.
            # This correctly counts how many times `p` is the predicate in a statement!
            usage["object_props"][p] += len(triples)

        for p in usage["data_props"]:
            triples = list(g.triples((None, p, None)))
            usage["data_props"][p] += len(triples)

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")


def get_local_name(uri):
    return str(uri).split("/")[-1].split("#")[-1]


def print_category(name, data):
    # Convert URIs to local names for display
    local_data = {get_local_name(k): v for k, v in data.items()}
    never_used = [k for k, v in local_data.items() if v == 0]
    rarely_used = [k for k, v in local_data.items() if 0 < v <= 2]
    often_used = [k for k, v in local_data.items() if v > 2]

    print(f"\n=== {name.upper()} ===")
    print(
        f"Never Used ({len(never_used)}): \n"
        + "\n".join(f"  - {k}" for k in sorted(never_used))
    )
    print(
        f"\nRarely Used 1-2x ({len(rarely_used)}): \n"
        + "\n".join(f"  - {k} ({local_data[k]})" for k in sorted(rarely_used))
    )
    print(
        f"\nOften Used >2x ({len(often_used)}): \n"
        + "\n".join(f"  - {k} ({local_data[k]})" for k in sorted(often_used))
    )


print_category("Classes", usage["classes"])
print_category("Object Properties", usage["object_props"])
print_category("Data Properties", usage["data_props"])
