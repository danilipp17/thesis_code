"""
evaluation.fixtures
===================
Hand-authored ground-truth artifacts used by the generation-only pipeline.

Two kinds of fixtures are supported:

1. **Seed scripts** (``seed_*.py``): build an :class:`~oscin.intermediate`
   graph in Python, run the populator, and write a ``.ttl`` file next
   to themselves. Run once per edit to regenerate.

2. **Static TTL files** (``*.ttl``): hand-written or previously produced
   gold-standard graphs that can be fed directly to
   :mod:`evaluation.pipelines.generation`.

The generation pipeline resolves ``--fixture NAME`` to
``evaluation/fixtures/NAME.ttl``.
"""
