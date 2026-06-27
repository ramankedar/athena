"""Interfaces — delivery mechanisms for the Athena platform.

The interfaces layer is the outermost ring of the hexagonal architecture.
It is the only layer authorised to handle user input, CLI arguments, HTTP
requests, and scheduled triggers. It translates external inputs into
application-layer commands and renders results back to callers.

Current interfaces:
    cli/    — command-line interface (typer)

Planned interfaces:
    api/    — REST/WebSocket API for the risk dashboard (FastAPI)
"""
