import re
import glob
from collections import defaultdict

ontology_file = "ontology/agentoscin.ttl"
generated_files = glob.glob("output/**/*.ttl", recursive=True) + ["custom_system.ttl"]

# Parse ontology classes and properties
with open(ontology_file, "r", encoding="utf-8") as f:
    onto_content = f.read()

classes = re.findall(
    r"^:([A-Z][a-zA-Z0-9_]+)\s+rdf:type owl:Class", onto_content, re.MULTILINE
)
object_props = re.findall(
    r"^:([a-z][a-zA-Z0-9_]+)\s+rdf:type owl:ObjectProperty", onto_content, re.MULTILINE
)
data_props = re.findall(
    r"^:([a-z][a-zA-Z0-9_]+)\s+rdf:type owl:DatatypeProperty",
    onto_content,
    re.MULTILINE,
)

# Counters
usage = {
    "classes": {c: 0 for c in classes},
    "object_props": {p: 0 for p in object_props},
    "data_props": {p: 0 for p in data_props},
}

for filepath in generated_files:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    for c in classes:
        usage["classes"][c] += len(re.findall(rf"\b{c}\b", content))
    for p in object_props:
        usage["object_props"][p] += len(re.findall(rf"\b{p}\b", content))
    for p in data_props:
        usage["data_props"][p] += len(re.findall(rf"\b{p}\b", content))


def print_category(name, data):
    print(f"\n=== {name.upper()} ===")
    never_used = [k for k, v in data.items() if v == 0]
    rarely_used = [k for k, v in data.items() if 0 < v <= 2]
    often_used = [k for k, v in data.items() if v > 2]

    print(f"\nNever Used ({len(never_used)}):")
    for k in sorted(never_used):
        print(f"  - {k}")

    print(f"\nRarely Used (1-2 times) ({len(rarely_used)}):")
    for k in sorted(rarely_used):
        print(f"  - {k} ({data[k]} times)")

    print(f"\nOften Used (>2 times) ({len(often_used)}):")
    for k in sorted(often_used):
        print(f"  - {k} ({data[k]} times)")


print_category("Classes", usage["classes"])
print_category("Object Properties", usage["object_props"])
print_category("Data Properties", usage["data_props"])
