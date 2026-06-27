"""Athena command-line interface.

Entry point: `athena` (configured in pyproject.toml [project.scripts])
Alternatively: `python -m athena.interfaces.cli`

Sub-commands (to be added as engines are implemented):
    athena version     — print version and exit
    athena status      — show platform health summary
    athena data        — data engine commands
    athena backtest    — run a backtest
"""

from __future__ import annotations

import sys
from typing import Annotated

import typer

import athena

app = typer.Typer(
    name="athena",
    help="Athena — AI-powered quantitative research and automated trading platform.",
    add_completion=False,
    pretty_exceptions_show_locals=False,  # Never log locals; may contain secrets.
)


@app.command()
def version(
    short: Annotated[bool, typer.Option("--short", "-s", help="Print version only")] = False,
) -> None:
    """Print the Athena platform version."""
    if short:
        typer.echo(athena.__version__)
    else:
        typer.echo(f"Athena {athena.__version__}")
        typer.echo(f"Python {sys.version.split()[0]}")


@app.command()
def status() -> None:
    """Show platform health summary (engines, services, configuration)."""
    # Implementation added when the platform layer is wired up.
    typer.echo("Athena status: scaffold only — engines not yet wired.")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
