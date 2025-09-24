"""Enhanced CLI commands with comprehensive security measures for Qwen Code."""

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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rich_print

# For keyboard event handling
import threading
import queue

# Import our enhanced interactive input
from qwen_code.cli.interactive_input import InteractiveInput, Command as InteractiveCommand
from qwen_code.cli.ui import EnhancedUI, THEMES

# Import security modules
from qwen_code.security.validation import InputValidator, input_validator
from qwen_code.security.rate_limiting import api_rate_limiter
from qwen_code.security.audit import security_monitor, SecurityEventType
from qwen_code.security.credentials import SecureCredentials, SecureCredentialManager

console = Console()
logger = get_logger()


@click.command()
@click.option('--interactive', is_flag=True, default=True, help='Start interactive session')
@click.option('--model', default='qwen3-coder-plus', help='AI model to use')
@click.option('--theme', default=None, help='UI theme to use')
def chat(interactive: bool, model: str, theme: str) -> None:
    """Start AI conversation session."""
    # Validate inputs for security
    if not input_validator.validate_filename(model.replace('/', '_').replace('\\', '_')):
        logger.error(f"Invalid model name: {model}")
        console.print(f"[red]ERROR:[/red] Invalid model name: {model}")
        return
    
    if theme and not input_validator.validate_filename(theme.replace('/', '_').replace('\\', '_')):
        logger.error(f"Invalid theme name: {theme}")
        console.print(f"[red]ERROR:[/red] Invalid theme name: {theme}")
        return

    try:
        if interactive:
            # Run the interactive session
            asyncio.run(_run_interactive_session(model, theme))
        else:
            console.print(f"[blue]Using model:[/blue] {model}")
    except Exception as e:
        logger.error(f"Error in chat command: {str(e)}")
        console.print(f"[red]ERROR:[/red] {str(e)}")


async def _run_interactive_session(model: str, theme: str = None) -> None:
    """Run the interactive conversation session with security measures."""
    try:
        # Initialize the application
        app = QwenCodeApplication()
        await app.initialize()
        
        # Get the AI client based on configuration
        from qwen_code.ai.client import QwenClient
        from qwen_code.config.settings import Config
        
        config = Config()
        await config.load()
        
        # Use provided theme, or fall back to config theme, or default
        if theme is None:
            theme = config.ui_theme  # Use theme from config
            
        # For Qwen OAuth, we don't need to pass the API key directly
        # The QwenClient will use our enhanced OAuth2 client to get the proper API key
        api_key = None
        is_oauth_token = False
        # Removed debug prints for cleaner UI
        if config.auth_provider == "qwen_oauth":
            # For Qwen OAuth, we'll let the QwenClient handle authentication
            # The enhanced OAuth2 client will be used automatically
            pass  # Removed debug print
        else:
            # Try to get from providers config
            provider_config = config.providers.get(config.auth_provider)
            if provider_config:
                api_key = provider_config.api_key
                # Removed debug print
        
        # Create AI client - for Qwen OAuth, it will use our enhanced OAuth2 client automatically
        ai_client = QwenClient(api_key=api_key, model=model, is_oauth_token=is_oauth_token)
        
        # Initialize UI with theme support
        ui = EnhancedUI(theme)
        
        # Initialize interactive input with commands
        interactive_commands = [
            InteractiveCommand("help", "Display available commands"),
            InteractiveCommand("clear", "Clear conversation history"),
            InteractiveCommand("compress", "Compress history to save tokens"),
            InteractiveCommand("stats", "Show current session information"),
            InteractiveCommand("exit", "Exit Qwen Code", alt_names=["quit"]),
            InteractiveCommand("auth", "Authentication management"),
            InteractiveCommand("session", "Session management"),
            InteractiveCommand("config", "Configuration management"),
            InteractiveCommand("theme", "Change UI theme"),
        ]
        interactive_input = InteractiveInput(interactive_commands)
        
        # Display welcome message with enhanced UI
        ui.print_welcome()
        
        # If theme was changed via command, update config
        if theme != config.ui_theme:
            config.ui_theme = theme
            config.save()  # Save the theme to persistent storage
        
        # Main conversation loop
        messages = []
        
        # Log session creation to file only (not to console for cleaner UI)
        # security_monitor.log_and_monitor(
        #     SecurityEventType.SESSION_CREATION,
        #     user_id="current_user",
        #     ip_address=None,
        #     details={"session_type": "interactive", "model": model}
        # )
        
        while True:
            try:
                # Get user input with enhanced interactive input handling
                user_input = interactive_input.run()
                
                # Sanitize user input
                sanitized_input = input_validator.sanitize_input(user_input)
                
                # Check for command injection attempts
                if not input_validator.validate_command_input(sanitized_input):
                    # Only log to file, not to console for cleaner UI
                    # logger.warning(f"Potentially dangerous command blocked: {sanitized_input[:100]}...")
                    ui.print_error("Command blocked for security reasons")
                    continue
                
                # Special handling for keyboard interrupts
                if sanitized_input == 'exit':
                    ui.print_info("Goodbye!")
                    break
                
                # Check for special commands
                if sanitized_input.startswith('/'):
                    # Normalize the command by stripping trailing spaces and extracting the command part
                    cmd_parts = sanitized_input.strip().split()
                    cmd = cmd_parts[0] if cmd_parts else sanitized_input.strip()
                    
                    # Check rate limit for command usage
                    user_id = "current_user"  # In a real scenario, this would be actual user ID
                    is_allowed, rate_info = api_rate_limiter.check_rate_limit("chat_api", user_id)
                    if not is_allowed:
                        ui.print_error(f"Rate limit exceeded. Try again in {rate_info['reset_time']} seconds")
                        continue
                    
                    if cmd == '/help':
                        ui.show_help()
                        continue
                    elif cmd == '/clear':
                        messages = []
                        ui.print_info("Conversation history cleared")
                        continue
                    elif cmd == '/stats':
                        ui.show_stats(messages)
                        continue
                    elif cmd == '/status':
                        ui.show_status()
                        continue
                    elif cmd == '/auth':
                        # Execute the auth command with potential sub-arguments
                        # Extract potential sub-arguments from the input
                        auth_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                        
                        try:
                            # Process arguments for auth command
                            if len(auth_args) == 0:
                                # No provider specified, show help - just call the function directly
                                auth(None, False)
                            else:
                                # Check if --device flag is present
                                device_flag = '--device' in auth_args
                                # Remove the --device flag if present to get the provider
                                clean_args = [arg for arg in auth_args if arg != '--device']
                                provider = clean_args[0] if clean_args else None
                                # Call the auth function directly
                                auth(provider, device_flag)
                        except Exception as e:
                            ui.print_error(f"Error executing auth command: {str(e)}")
                        continue
                    elif cmd == '/config':
                        # Execute the config command with potential sub-arguments
                        config_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                        
                        try:
                            # Determine if this is a subcommand like 'list', 'get', or 'set'
                            if len(config_args) == 0:
                                # Default to list config - call directly
                                list_config()
                            elif config_args and config_args[0] in ['list', 'get', 'set']:
                                # Process subcommand
                                subcmd = config_args[0]
                                if subcmd == 'list':
                                    list_config()
                                elif subcmd == 'get' and len(config_args) >= 2:
                                    # get command with key: /config get key_name
                                    get_config(config_args[1], None)
                                elif subcmd == 'set' and len(config_args) >= 3:
                                    # set command with key and value: /config set key_name value
                                    get_config(config_args[1], config_args[2])
                                else:
                                    # Invalid subcommand or missing arguments 
                                    ui.print_error(f"Invalid config command: {' '.join(config_args)}")
                                    ui.print_info("Usage: /config list | /config get <key> | /config set <key> <value>")
                            else:
                                # Invalid config command
                                ui.print_error(f"Invalid config command: {' '.join(config_args)}")
                                ui.print_info("Usage: /config list | /config get <key> | /config set <key> <value>")
                        except Exception as e:
                            ui.print_error(f"Error executing config command: {str(e)}")
                        continue
                    elif cmd == '/theme':
                        if len(cmd_parts) > 1:
                            new_theme = cmd_parts[1]
                            if new_theme in THEMES:
                                ui.set_theme(new_theme)
                                ui.print_success(f"Theme changed to {new_theme}")
                            else:
                                ui.print_error(f"Unknown theme: {new_theme}")
                                ui.print_info(f"Available themes: {', '.join(THEMES.keys())}")
                        else:
                            ui.show_themes()
                        continue
                    elif cmd in ['/quit', '/exit']:
                        ui.print_info("Goodbye!")
                        break
                    elif cmd == '/session':
                        # Handle session commands
                        session_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                        
                        if len(session_args) == 0:
                            ui.print_info("Session management commands: /session list, /session save, /session load")
                        elif session_args[0] == 'list':
                            ui.print_info("Session list functionality would be implemented here")
                        elif session_args[0] == 'save':
                            ui.print_info("Session save functionality would be implemented here")
                        elif session_args[0] == 'load':
                            ui.print_info("Session load functionality would be implemented here")
                        else:
                            ui.print_error(f"Unknown session command: {' '.join(session_args)}")
                            ui.print_info("Usage: /session list | /session save | /session load")
                        continue
                    elif cmd == '/version':
                        # Execute the version command
                        try:
                            version()
                        except Exception as e:
                            ui.print_error(f"Error executing version command: {str(e)}")
                        continue
                    else:
                        ui.print_warning("Unknown command. Type '/help' for available commands.")
                        continue
                
                # Check rate limit before processing user message
                user_id = "current_user"
                is_allowed, rate_info = api_rate_limiter.check_rate_limit("chat_api", user_id)
                if not is_allowed:
                    ui.print_error(f"Rate limit exceeded. Try again in {rate_info['reset_time']} seconds")
                    continue
                
                # Add user message to conversation
                user_message = Message(role="user", content=sanitized_input)
                messages.append(user_message)
                
                # Show thinking indicator during AI processing
                from rich.live import Live
                
                # Create the progress indicator
                progress, task_id = ui.show_thinking_indicator("Thinking...")
                
                # Run the AI chat request and show progress concurrently
                with Live(progress, console=console):
                    response = await ai_client.chat(messages)
                    # Update the task to completed state
                    progress.update(task_id, completed=True)
                
                # Add AI response to conversation
                ai_message = Message(role="assistant", content=response.content)
                messages.append(ai_message)
                
                # Display AI response with enhanced formatting
                ui.print_ai_response(response.content)
                
            except KeyboardInterrupt:
                ui.print_warning("Session interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error during conversation: {str(e)}")
                ui.print_error(str(e))
                
    except Exception as e:
        logger.error(f"Failed to start interactive session: {str(e)}")
        console.print(f"[red]ERROR:[/red] Failed to start interactive session: {str(e)}")
    finally:
        # Log session destruction to file only (not to console for cleaner UI)
        # security_monitor.log_and_monitor(
        #     SecurityEventType.SESSION_DESTRUCTION,
        #     user_id="current_user",
        #     ip_address=None,
        #     details={"session_type": "interactive", "model": model}
        # )
        
        # Clean up application resources
        # Use the same app instance that was initialized earlier in the function
        if 'app' in locals() and app.db_manager:
            try:
                await app.cleanup()
            except Exception as e:
                logger.error(f"Error during application cleanup: {str(e)}")


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


def _show_status():
    """Show session status information."""
    status_table = Table(title="Session Status", show_header=True, header_style="bold cyan")
    status_table.add_column("Property", style="magenta")
    status_table.add_column("Value", style="white")
    
    import datetime
    status_table.add_row("Status", "Active")
    status_table.add_row("Model", "qwen3-coder-plus")
    status_table.add_row("Created", str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    status_table.add_row("Last Activity", str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    console.print(status_table)


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
    """Manage authentication with security measures."""
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
        
        # Validate provider name
        if not input_validator.validate_filename(provider.replace('/', '_').replace('\\', '_')):
            logger.error(f"Invalid provider name: {provider}")
            console.print(f"[red]ERROR:[/red] Invalid provider name: {provider}")
            return
        
        # Check rate limit for authentication attempts
        user_id = "current_user"  # In a real scenario, this would be the actual user ID
        is_allowed, rate_info = api_rate_limiter.check_rate_limit("auth_api", user_id)
        if not is_allowed:
            console.print(f"[red]Rate limit exceeded:[/red] Too many authentication attempts. Try again in {rate_info['reset_time']} seconds")
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
                        security_monitor.log_and_monitor(
                            SecurityEventType.AUTHENTICATION_FAILURE,
                            user_id=user_id,
                            ip_address=None,
                            details={"provider": provider, "reason": "Provider not configured"}
                        )
                        return
                    
                    # Validate client ID and redirect URI
                    if not input_validator.validate_api_key(provider_config.client_id or ""):
                        console.print("[red]ERROR:[/red] Invalid client configuration")
                        security_monitor.log_and_monitor(
                            SecurityEventType.AUTHENTICATION_FAILURE,
                            user_id=user_id,
                            ip_address=None,
                            details={"provider": provider, "reason": "Invalid client configuration"}
                        )
                        return
                    
                    # Create OAuth provider
                    oauth_provider = QwenOAuthProvider(
                        client_id=provider_config.client_id or "f0304373b74a44d2b584a3fb70ca9e56",
                        redirect_uri=provider_config.redirect_uri or "http://localhost:8080/callback"
                    )
                    
                    # Perform authentication
                    console.print("[blue]Starting Qwen OAuth authentication...[/blue]")
                    import asyncio
                    try:
                        auth_result = asyncio.run(oauth_provider.authenticate(use_device_flow=device))
                    except Exception as e:
                        console.print(f"[red]Authentication error:[/red] {str(e)}")
                        security_monitor.log_and_monitor(
                            SecurityEventType.AUTHENTICATION_FAILURE,
                            user_id=user_id,
                            ip_address=None,
                            details={"provider": provider, "reason": f"Authentication error: {str(e)}"}
                        )
                        return
                else:
                    console.print(f"[yellow]Provider {provider} not fully implemented in this demo[/yellow]")
                    console.print("[blue]In a full implementation, this would start the OAuth flow[/blue]")
                    return
                
                if not auth_result.success:
                    console.print(f"[red]Authentication failed:[/red] {auth_result.error_message}")
                    security_monitor.log_and_monitor(
                        SecurityEventType.AUTHENTICATION_FAILURE,
                        user_id=user_id,
                        ip_address=None,
                        details={"provider": provider, "reason": auth_result.error_message}
                    )
                    return
                
                # Validate the received access token
                if not input_validator.validate_api_key(auth_result.access_token):
                    console.print("[red]ERROR:[/red] Invalid access token received from authentication")
                    security_monitor.log_and_monitor(
                        SecurityEventType.AUTHENTICATION_FAILURE,
                        user_id=user_id,
                        ip_address=None,
                        details={"provider": provider, "reason": "Invalid access token received"}
                    )
                    return
                
                # Store credentials using the auth credential manager
                from qwen_code.auth.credentials import CredentialManager as AuthCredentialManager
                from qwen_code.auth.providers import Credentials as AuthCredentials
                from datetime import datetime, timedelta
                cred_manager = AuthCredentialManager()
                
                # Calculate expiration time if available
                expires_at = None
                if hasattr(auth_result, 'expires_at') and auth_result.expires_at:
                    expires_at = auth_result.expires_at
                elif auth_result.access_token:
                    # Default to 1 hour if not provided
                    expires_at = datetime.now() + timedelta(hours=1)
                
                # Create auth credentials object for encrypted storage
                credentials = AuthCredentials(
                    provider=f"{provider}_oauth",
                    access_token=auth_result.access_token,
                    refresh_token=getattr(auth_result, 'refresh_token', None),
                    expires_at=expires_at.isoformat() if expires_at else None,
                    client_id=provider_config.client_id
                )
                
                # Store credentials securely in encrypted database
                cred_manager.store_credentials(credentials)
                
                console.print("[green]Authentication successful![/green]")
                console.print("[blue]Credentials have been securely stored.[/blue]")
                
                # Log successful authentication
                security_monitor.log_and_monitor(
                    SecurityEventType.AUTHENTICATION_SUCCESS,
                    user_id=user_id,
                    ip_address=None,
                    details={"provider": provider}
                )
                
            except Exception as e:
                console.print(f"[red]Authentication failed:[/red] {str(e)}")
                security_monitor.log_and_monitor(
                    SecurityEventType.AUTHENTICATION_FAILURE,
                    user_id=user_id,
                    ip_address=None,
                    details={"provider": provider, "reason": str(e)}
                )
                return
        else:
            console.print(f"[red]Unknown provider:[/red] {provider}")
            console.print("[blue]Available providers:[/blue] qwen, openai")
            security_monitor.log_and_monitor(
                SecurityEventType.AUTHENTICATION_FAILURE,
                user_id=user_id,
                ip_address=None,
                details={"provider": provider, "reason": "Unknown provider"}
            )
    except Exception as e:
        logger.error(f"Error in auth command: {str(e)}")
        console.print(f"[red]ERROR:[/red] {str(e)}")
        # Only log to file, not to console for cleaner UI
        # security_monitor.log_and_monitor(
        #     SecurityEventType.AUTHENTICATION_FAILURE,
        #     user_id="current_user",
        #     ip_address=None,
        #     details={"reason": f"Auth command error: {str(e)}"}
        # )


@click.group()
def config():
    """Manage configuration settings."""
    pass


@click.command()
def list_config():
    """List all configuration settings with security monitoring."""
    from qwen_code.config.settings import Config
    
    # Check rate limit for configuration access
    user_id = "current_user"
    is_allowed, rate_info = api_rate_limiter.check_rate_limit("config_api", user_id)
    if not is_allowed:
        console.print(f"[red]Rate limit exceeded:[/red] Too many configuration requests. Try again in {rate_info['reset_time']} seconds")
        return
    
    # Handle asyncio event loop for the config load
    try:
        config = Config()
        if sys.platform.startswith("win"):
            # On Windows, we may need to handle event loops differently
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, use a different approach
                    import threading
                    def load_config():
                        asyncio.run(config.load())
                    thread = threading.Thread(target=load_config)
                    thread.start()
                    thread.join()
                else:
                    asyncio.run(config.load())
            except RuntimeError:
                # If no event loop is running, create one
                asyncio.run(config.load())
        else:
            asyncio.run(config.load())
    except Exception:
        # Fallback: just initialize the config without loading
        config = Config()
    
    settings_table = Table(
        title="Configuration Settings",
        show_header=True,
        header_style="bold magenta"
    )
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="white")
    
    settings_table.add_row("Authentication Provider", config.auth_provider)
    settings_table.add_row("Default Model", config.model_settings.default_model)
    settings_table.add_row("Temperature", str(config.model_settings.temperature))
    settings_table.add_row("Max Tokens", str(config.model_settings.max_tokens))
    settings_table.add_row("Session Token Limit", str(config.session_config.token_limit))
    settings_table.add_row("Auto Save", str(config.session_config.auto_save))
    settings_table.add_row("UI Theme", config.ui_theme)
    
    console.print(settings_table)
    
    # Only log to file, not to console for cleaner UI
    # security_monitor.log_and_monitor(
    #     SecurityEventType.CONFIG_CHANGE,
    #     user_id=user_id,
    #     ip_address=None,
    #     details={"action": "list_config"}
    # )


@click.command()
@click.argument('key')
@click.argument('value', required=False)
def get_config(key: str, value: str = None):
    """Get or set a configuration value with security validation."""
    from qwen_code.config.settings import Config
    
    # Validate key name for security
    if not input_validator.validate_filename(key.replace('/', '_').replace('\\', '_')):
        logger.error(f"Invalid configuration key: {key}")
        console.print(f"[red]ERROR:[/red] Invalid configuration key: {key}")
        return
    
    # Check rate limit for configuration operations
    user_id = "current_user"
    is_allowed, rate_info = api_rate_limiter.check_rate_limit("config_api", user_id)
    if not is_allowed:
        console.print(f"[red]Rate limit exceeded:[/red] Too many configuration requests. Try again in {rate_info['reset_time']} seconds")
        return
    
    # Validate value if provided
    if value and not input_validator.validate_filename(value.replace('/', '_').replace('\\', '_')):
        logger.error(f"Invalid configuration value: {value}")
        console.print(f"[red]ERROR:[/red] Invalid configuration value: {value}")
        return
    
    # Handle asyncio event loop for the config load
    try:
        config = Config()
        if sys.platform.startswith("win"):
            # On Windows, we may need to handle event loops differently
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, use a different approach
                    import threading
                    def load_config():
                        asyncio.run(config.load())
                    thread = threading.Thread(target=load_config)
                    thread.start()
                    thread.join()
                else:
                    asyncio.run(config.load())
            except RuntimeError:
                # If no event loop is running, create one
                asyncio.run(config.load())
        else:
            asyncio.run(config.load())
    except Exception:
        # Fallback: just initialize the config without loading
        config = Config()
    
    if value is None:
        # Get the value
        if key == "auth_provider":
            console.print(f"[cyan]auth_provider:[/cyan] {config.auth_provider}")
        elif key == "default_model":
            console.print(f"[cyan]default_model:[/cyan] {config.model_settings.default_model}")
        elif key == "temperature":
            console.print(f"[cyan]temperature:[/cyan] {config.model_settings.temperature}")
        elif key == "max_tokens":
            console.print(f"[cyan]max_tokens:[/cyan] {config.model_settings.max_tokens}")
        elif key == "token_limit":
            console.print(f"[cyan]token_limit:[/cyan] {config.session_config.token_limit}")
        elif key == "auto_save":
            console.print(f"[cyan]auto_save:[/cyan] {config.session_config.auto_save}")
        elif key == "ui_theme":
            console.print(f"[cyan]ui_theme:[/cyan] {config.ui_theme}")
        else:
            console.print(f"[red]Unknown configuration key:[/red] {key}")
            console.print("[blue]Available keys:[/blue] auth_provider, default_model, temperature, max_tokens, token_limit, auto_save, ui_theme")
    else:
        # Set the value
        old_value = None
        
        if key == "auth_provider":
            old_value = config.auth_provider
            config.auth_provider = value
            console.print(f"[green]Updated auth_provider to:[/green] {value}")
        elif key == "default_model":
            old_value = config.model_settings.default_model
            config.model_settings.default_model = value
            console.print(f"[green]Updated default_model to:[/green] {value}")
        elif key == "temperature":
            try:
                old_value = config.model_settings.temperature
                config.model_settings.temperature = float(value)
                console.print(f"[green]Updated temperature to:[/green] {value}")
            except ValueError:
                console.print(f"[red]Invalid temperature value:[/red] {value}")
                return
        elif key == "max_tokens":
            try:
                old_value = config.model_settings.max_tokens
                config.model_settings.max_tokens = int(value)
                console.print(f"[green]Updated max_tokens to:[/green] {value}")
            except ValueError:
                console.print(f"[red]Invalid max_tokens value:[/red] {value}")
                return
        elif key == "token_limit":
            try:
                old_value = config.session_config.token_limit
                config.session_config.token_limit = int(value)
                console.print(f"[green]Updated token_limit to:[/green] {value}")
            except ValueError:
                console.print(f"[red]Invalid token_limit value:[/red] {value}")
                return
        elif key == "auto_save":
            old_value = config.session_config.auto_save
            config.session_config.auto_save = value.lower() in ['true', '1', 'yes', 'on']
            console.print(f"[green]Updated auto_save to:[/green] {config.session_config.auto_save}")
        elif key == "ui_theme":
            from qwen_code.cli.ui import THEMES
            if value in THEMES:
                old_value = config.ui_theme
                config.ui_theme = value
                console.print(f"[green]Updated ui_theme to:[/green] {value}")
            else:
                console.print(f"[red]Invalid theme:[/red] {value}")
                console.print(f"[blue]Available themes:[/blue] {', '.join(THEMES.keys())}")
                return
        else:
            console.print(f"[red]Unknown configuration key:[/red] {key}")
            console.print("[blue]Available keys:[/blue] auth_provider, default_model, temperature, max_tokens, token_limit, auto_save, ui_theme")
            return
        
        # Save the updated configuration
        try:
            config.save()
            console.print("[green]Configuration saved successfully![/green]")
            
            # Only log to file, not to console for cleaner UI
            # new_value_for_log = value
            # if key in ["temperature"]:
            #     new_value_for_log = float(value)
            # elif key in ["max_tokens", "token_limit"]:
            #     new_value_for_log = int(value)
            # 
            # security_monitor.log_and_monitor(
            #     SecurityEventType.CONFIG_CHANGE,
            #     user_id=user_id,
            #     ip_address=None,
            #     details={
            #         "key": key,
            #         "old_value": str(old_value),
            #         "new_value": str(new_value_for_log)
            #     }
            # )
        except Exception as e:
            console.print(f"[red]Error saving configuration:[/red] {str(e)}")


# Add subcommands to config group
config.add_command(list_config, name="list")
config.add_command(get_config, name="set")
config.add_command(get_config, name="get")