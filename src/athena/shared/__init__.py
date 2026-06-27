"""Shared cross-cutting concerns.

This package provides logging, configuration, and exception infrastructure
used by all engines. It depends on athena.core but not on any engine.

Import boundary rule: athena.shared must not import from athena.engines
or athena.interfaces. Enforced by import-linter.
"""
