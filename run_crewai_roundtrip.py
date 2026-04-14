import sys
from oscin.cli import main
import os

print("--- EXTRACTION ---")
sys.argv = [
    'oscin', 'extract', 
    '--framework', 'crewai', 
    '--system-name', 'email-flow', 
    '--output', r'C:\Users\Dani\Thesis\Extractor\output\crewai\email-flow.ttl', 
    r'C:\Users\Dani\Thesis\Extractor\examples\crewai\email-flow\source_files'
]
try:
    main()
except SystemExit as e:
    print(f"Extraction exited with code {e.code}")

print("\n--- GENERATION ---")
sys.argv = [
    'oscin', 'generate', 
    '--target-framework', 'crewai', 
    '--output-dir', r'C:\Users\Dani\Thesis\Extractor\generated\crewai\email-flow', 
    r'C:\Users\Dani\Thesis\Extractor\output\crewai\email-flow.ttl'
]
try:
    main()
except SystemExit as e:
    print(f"Generation exited with code {e.code}")
