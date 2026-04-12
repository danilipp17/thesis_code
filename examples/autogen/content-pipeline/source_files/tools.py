"""Tool definitions for the content pipeline."""

import os
import requests


def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for information on a given query.
    Returns titles, snippets, and URLs of relevant results."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Error: SERPER_API_KEY not set."

    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "num": num_results},
    )
    results = response.json().get("organic", [])
    output = []
    for r in results[:num_results]:
        output.append(f"- {r.get('title', '')}: {r.get('snippet', '')} ({r.get('link', '')})")
    return "\n".join(output) if output else "No results found."


def word_count(text: str) -> str:
    """Counts the number of words in a given text."""
    count = len(text.split())
    return f"Word count: {count}"
