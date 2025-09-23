import click
import asyncio
import sys
from typing import Optional
from qwen_code.ai.client import Message
from qwen_code.app import QwenCodeApplication
from qwen_code.utils.logging import get_logger

# Rich imports for enhanced UI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rich_print

# For keyboard event handling
import threading
import queue

# Import our enhanced keyboard handler
from qwen_code.cli.keyboard_handler import KeyboardHandler

console = Console()
logger = get_logger()


@click.command()
@click.option('--interactive', is_flag=True, default=True, help='Start interactive session')
@click.option('--model', default='qwen3-coder-plus', help='AI model to use')
def chat(interactive: bool, model: str) -> None:
    """Start AI conversation session."""
    try:
        if interactive:
            # Run the interactive session
            asyncio.run(_run_interactive_session(model))
        else:
            console.print(f"[blue]Using model:[/blue] {model}")
    except Exception as e:
        logger.error(f"Error in chat command: {str(e)}")
        console.print(f"[red]ERROR:[/red] {str(e)}")


async def _run_interactive_session(model: str) -> None:
    """Run the interactive conversation session."""
    try:
        # Initialize the application
        app = QwenCodeApplication()
        await app.initialize()
        
        # Get the AI client based on configuration
        from qwen_code.ai.client import QwenClient
        from qwen_code.config.settings import Config
        
        config = Config()
        await config.load()
        
        # For Qwen OAuth, we don't need to pass the API key directly
        # The QwenClient will use our enhanced OAuth2 client to get the proper API key
        api_key = None
        is_oauth_token = False
        print(f"DEBUG: Auth provider: '{config.auth_provider}'")
        if config.auth_provider == "qwen_oauth":
            # For Qwen OAuth, we'll let the QwenClient handle authentication
            # The enhanced OAuth2 client will be used automatically
            print("DEBUG: Using Qwen OAuth authentication")
        else:
            # Try to get from providers config
            provider_config = config.providers.get(config.auth_provider)
            print(f"DEBUG: Provider config: {provider_config}")
            if provider_config:
                api_key = provider_config.api_key
                print(f"DEBUG: Using API key from config: {api_key[:20] if api_key else 'None'}")
        
        # Create AI client - for Qwen OAuth, it will use our enhanced OAuth2 client automatically
        ai_client = QwenClient(api_key=api_key, model=model, is_oauth_token=is_oauth_token)
        
        # Initialize keyboard handler
        keyboard_handler = KeyboardHandler()
        
        # Display welcome message with Rich panel
        welcome_panel = Panel(
            "[bold blue]Qwen Code[/bold blue] - AI-powered coding assistant\n"
            f"[blue]Model:[/blue] {model}\n"
            "[blue]Type[/blue] [green]'exit'[/green] [blue]or[/blue] [green]'quit'[/green] [blue]to end the session[/blue]\n"
            "[blue]Type[/blue] [green]'/help'[/green] [blue]for available commands[/blue]\n"
            "[blue]Press[/blue] [green]'/'[/green] [blue]at any time to see available commands[/blue]\n"
            "[blue]Press[/blue] [green]Tab[/green] [blue]for auto-completion[/blue]",
            title="Welcome",
            border_style="blue"
        )
        console.print(welcome_panel)
        
        # Main conversation loop
        messages = []
        
        while True:
            try:
                # Get user input with enhanced keyboard handling
                user_input = keyboard_handler.get_input_with_features()
                
                # Special handling for keyboard interrupts
                if user_input == 'exit':
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                
                # Check for special commands
                if user_input.startswith('/'):
                    if user_input == '/help':
                        _show_help()
                        continue
                    elif user_input == '/clear':
                        messages = []
                        console.print("[cyan]Conversation history cleared[/cyan]")
                        continue
                    elif user_input == '/stats':
                        _show_stats(messages)
                        continue
                    elif user_input == '/status':
                        _show_status()
                        continue
                    elif user_input == '/auth':
                        console.print("[yellow]Use 'qwen auth' command to manage authentication[/yellow]")
                        continue
                    elif user_input == '/config':
                        console.print("[yellow]Use 'qwen config' command to manage configuration[/yellow]")
                        continue
                    elif user_input == '/quit':
                        console.print("[yellow]Goodbye![/yellow]")
                        break
                    else:
                        console.print("[yellow]Unknown command. Type '/help' for available commands.[/yellow]")
                        continue
                
                # Add user message to conversation
                user_message = Message(role="user", content=user_input)
                messages.append(user_message)
                
                # Get AI response with progress indicator
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("[cyan]Thinking...", total=None)
                    response = await ai_client.chat(messages)
                    progress.remove_task(task)
                
                # Add AI response to conversation
                ai_message = Message(role="assistant", content=response.content)
                messages.append(ai_message)
                
                # Display AI response with Markdown formatting
                console.print("[bold blue]AI:[/bold blue]")
                md = Markdown(response.content)
                console.print(md)
                console.print()  # Empty line for readability
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Session interrupted. Goodbye![/yellow]")
                break
            except Exception as e:
                logger.error(f"Error during conversation: {str(e)}")
                console.print(f"[red]ERROR:[/red] {str(e)}")
                
    except Exception as e:
        logger.error(f"Failed to start interactive session: {str(e)}")
        console.print(f"[red]ERROR:[/red] Failed to start interactive session: {str(e)}")
    finally:
        # Clean up application resources
        try:
            app = QwenCodeApplication()
            await app.cleanup()
        except:
            pass


def _show_help() -> None:
    """Show available commands."""
    help_table = Table(title="Available Commands", show_header=True, header_style="bold magenta")
    help_table.add_column("Command", style="cyan", width=12)
    help_table.add_column("Description", style="white")
    
    help_table.add_row("/help", "Show this help message")
    help_table.add_row("/clear", "Clear conversation history")
    help_table.add_row("/stats", "Show conversation statistics")
    help_table.add_row("/status", "Show session status")
    help_table.add_row("/auth", "Manage authentication")
    help_table.add_row("/config", "Manage configuration")
    help_table.add_row("/quit", "Exit the session")
    
    console.print(help_table)
    console.print("[blue]Tips:[/blue]")
    console.print("  • Press [green]'/'[/green] at any time to see available commands")
    console.print("  • Press [green]Tab[/green] for auto-completion of commands")


def _show_stats(messages) -> None:
    """Show conversation statistics."""
    user_messages = sum(1 for msg in messages if msg.role == "user")
    assistant_messages = sum(1 for msg in messages if msg.role == "assistant")
    
    stats_table = Table(title="Conversation Statistics", show_header=True, header_style="bold magenta")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="white")
    
    stats_table.add_row("Total messages", str(len(messages)))
    stats_table.add_row("Your messages", str(user_messages))
    stats_table.add_row("AI responses", str(assistant_messages))
    
    console.print(stats_table)


@click.command()
def version() -> None:
    """Display version information."""
    try:
        from qwen_code import __version__
        version_panel = Panel(
            f"[bold blue]Qwen Code[/bold blue] v{__version__}\n"
            "[blue]AI-powered coding assistant[/blue]",
            title="Version",
            border_style="green"
        )
        console.print(version_panel)
    except Exception as e:
        logger.error(f"Error in version command: {str(e)}")
        console.print(f"[red]ERROR:[/red] {str(e)}")


@click.command()
@click.argument('provider', required=False)
@click.option('--device', is_flag=True, help='Use device code flow instead of web flow')
def auth(provider: Optional[str] = None, device: bool = False) -> None:
    """Manage authentication."""
    try:
        if provider is None:
            # Create a panel for authentication management
            auth_panel = Panel(
                "[bold blue]Authentication Management[/bold blue]\n\n"
                "[cyan]Available providers:[/cyan]\n"
                "  [green]qwen[/green]     - Qwen OAuth (Recommended)\n"
                "  [green]openai[/green]   - OpenAI Compatible API\n\n"
                "[blue]Usage:[/blue]\n"
                "  [yellow]qwen auth qwen[/yellow] [blue](for Qwen OAuth)[/blue]\n"
                "  [yellow]qwen auth qwen --device[/yellow] [blue](for device code flow)[/blue]\n"
                "  [yellow]qwen auth openai[/yellow] [blue](for OpenAI compatible API)[/blue]",
                title="Authentication",
                border_style="blue"
            )
            console.print(auth_panel)
            return
        
        # Handle provider authentication
        if provider in ["qwen", "openai"]:
            try:
                # Import OAuth provider
                if provider == "qwen":
                    from qwen_code.auth.providers import QwenOAuthProvider
                    from qwen_code.config.settings import Config
                    
                    # Get configuration
                    config = Config()
                    import asyncio
                    asyncio.run(config.load())
                    provider_config = config.providers.get("qwen_oauth")
                    
                    if not provider_config:
                        console.print("[red]ERROR:[/red] Qwen OAuth provider not configured")
                        return
                    
                    # Create OAuth provider
                    oauth_provider = QwenOAuthProvider(
                        client_id=provider_config.client_id or "f0304373b74a44d2b584a3fb70ca9e56",
                        redirect_uri=provider_config.redirect_uri or "http://localhost:8080/callback"
                    )
                    
                    # Perform authentication
                    console.print("[blue]Starting Qwen OAuth authentication...[/blue]")
                    import asyncio
                    auth_result = asyncio.run(oauth_provider.authenticate(use_device_flow=device))
                else:
                    console.print(f"[yellow]Provider {provider} not fully implemented in this demo[/yellow]")
                    console.print("[blue]In a full implementation, this would start the OAuth flow[/blue]")
                    return
                
                if not auth_result.success:
                    console.print(f"[red]Authentication failed:[/red] {auth_result.error_message}")
                    return
                
                # Store credentials using the credential manager
                from qwen_code.auth.credentials import CredentialManager, Credentials
                from datetime import datetime, timedelta
                cred_manager = CredentialManager()
                
                # Calculate expiration time if available
                expires_at = None
                if hasattr(auth_result, 'expires_at') and auth_result.expires_at:
                    expires_at = auth_result.expires_at
                elif auth_result.access_token:
                    # Default to 1 hour if not provided
                    expires_at = datetime.now() + timedelta(hours=1)
                
                # Create credentials object for encrypted storage
                credentials = Credentials(
                    provider=f"{provider}_oauth",
                    access_token=auth_result.access_token,
                    refresh_token=getattr(auth_result, 'refresh_token', None),
                    expires_at=expires_at.isoformat() if expires_at else None
                )
                
                # Store credentials securely in encrypted database
                cred_manager.store_credentials(credentials)
                
                # Also save to JSON file for compatibility with OAuth client
                token_data = {
                    'access_token': auth_result.access_token,
                    'refresh_token': getattr(auth_result, 'refresh_token', None),
                    'expires_at': expires_at.isoformat() if expires_at else None
                }
                cred_manager.save_tokens_to_json(token_data)
                
                console.print("[green]Authentication successful![/green]")
                console.print("[blue]Credentials have been securely stored.[/blue]")
                
            except Exception as e:
                console.print(f"[red]Authentication failed:[/red] {str(e)}")
                return
        else:
            console.print(f"[red]Unknown provider:[/red] {provider}")
            console.print("[blue]Available providers:[/blue] qwen, openai")
    except Exception as e:
        logger.error(f"Error in auth command: {str(e)}")
        console.print(f"[red]ERROR:[/red] {str(e)}")
