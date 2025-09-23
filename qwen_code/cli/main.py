"""Main entry point for the Qwen Code CLI application."""

import asyncio
import sys
from typing import Optional
import click
from qwen_code.app import QwenCodeApplication
from qwen_code.cli.commands import chat, version, auth


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version information')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def main(ctx: click.Context, version: bool, debug: bool) -> int:
    """Qwen Code CLI - AI-powered coding assistant."""
    if version:
        from qwen_code import __version__
        click.echo(f"Qwen Code v{__version__}")
        return 0
    
    # If no command is specified, start interactive mode by default
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)
        return 0
    
    return 0


# Register commands
main.add_command(chat)
main.add_command(version)
main.add_command(auth)


def create_app() -> QwenCodeApplication:
    """Create and configure the main application instance.
    
    Returns:
        QwenCodeApplication: Configured application instance
    """
    return QwenCodeApplication()


if __name__ == '__main__':
    sys.exit(main())