"""Port interfaces (Protocols) for infrastructure adapters.

Every port is a `typing.Protocol` with `runtime_checkable=True`. This means:
    - mypy validates implementations at the type-check level
    - `isinstance(adapter, SomePort)` works at runtime for guards

Adapters implementing these ports live in each engine's `infrastructure/`
layer. The domain core and application layers depend only on these protocols,
never on concrete implementations.
"""
