"""
evaluation.pipelines
====================
Three clearly separated evaluation pipelines:

- :mod:`evaluation.pipelines.extraction` — source code → TTL + metrics.
- :mod:`evaluation.pipelines.generation` — TTL → source code + metrics.
- :mod:`evaluation.pipelines.roundtrip`  — source → TTL → source' (same or
  cross framework) + metrics comparing both endpoints.

Each pipeline writes its report under ``output/<pipeline>/``.
"""
