"""Command line interface for the Edge TTS toolkit."""

from __future__ import annotations

import typer

from . import __version__

app = typer.Typer(help="Work with large text-to-speech jobs using edge-tts.")


@app.callback()
def main() -> None:
    """Root command callback."""


@app.command()
def version() -> None:
    """Display the package version."""

    typer.echo(f"tts-edge version {__version__}")


def run() -> None:
    """Entrypoint for the console script."""

    app()


if __name__ == "__main__":
    run()
