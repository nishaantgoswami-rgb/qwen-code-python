"""Enhanced keyboard handling utilities for the Qwen Code CLI with improved terminal compatibility."""

import sys
import asyncio
from typing import List, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Try to import prompt_toolkit, but provide fallbacks
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.shortcuts import CompleteStyle
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False
    # Fallback imports if prompt_toolkit is not available
    import msvcrt
    try:
        import tty, termios
    except ImportError:
        pass


class EnhancedKeyboardHandler:
    """Enhanced keyboard handler with improved cross-platform terminal compatibility."""

    def __init__(self):
        self.commands = ["/help", "/clear", "/stats", "/status", "/auth", "/config", "/quit"]
        self.command_descriptions = {
            "/help": "Show available commands",
            "/clear": "Clear conversation history",
            "/stats": "Show conversation statistics",
            "/status": "Show session status",
            "/auth": "Manage authentication",
            "/config": "Manage configuration",
            "/quit": "Exit the session"
        }
        self.console = Console()
        self.session: Optional[PromptSession] = None
        self.bindings: Optional[KeyBindings] = None
        
        # Initialize prompt_toolkit if available
        if HAS_PROMPT_TOOLKIT:
            try:
                self.bindings = KeyBindings()
                self._setup_key_bindings()
                self.session = PromptSession(key_bindings=self.bindings)
            except Exception as e:
                # Fall back to basic functionality if prompt_toolkit encounters terminal issues
                self.console.print(f"[yellow]Warning: prompt_toolkit initialization failed: {e}[/yellow]")
                self.console.print("[yellow]Using basic input method.[/yellow]")
                self.session = None
                self.bindings = None

    def _setup_key_bindings(self):
        """Setup custom key bindings."""
        @self.bindings.add('/')
        def _(event):
            """Show help when / is pressed."""
            event.app.exit(result='/help_popup')

        @self.bindings.add('c-c')
        def _(event):
            """Handle Ctrl+C to exit."""
            event.app.exit(result='__keyboard_interrupt__')

        @self.bindings.add('c-d')
        def _(event):
            """Handle Ctrl+D to exit."""
            event.app.exit(result='__eof__')

    def _show_command_popup(self):
        """Show available commands in a Rich panel."""
        try:
            # Create a table with available commands
            table = Table(title="Available Commands", show_header=True, header_style="bold magenta")
            table.add_column("Command", style="cyan", width=12)
            table.add_column("Description", style="white")

            for command in self.commands:
                desc = self.command_descriptions.get(command, "")
                table.add_row(command, desc)

            # Print the table
            self.console.print(table)
            self.console.print("[blue]Tip:[/blue] Press [green]Tab[/green] for auto-completion")
            
            return True
        except Exception:
            # Fallback to simple print if Rich fails
            self.console.print("Available Commands:")
            for command in self.commands:
                desc = self.command_descriptions.get(command, "")
                self.console.print(f"{command} - {desc}")
            self.console.print("Tip: Press Tab for auto-completion")
            return True

    def _get_input_prompt_toolkit(self) -> str:
        """Get input using prompt_toolkit for better terminal compatibility."""
        if not HAS_PROMPT_TOOLKIT:
            raise ImportError("prompt_toolkit not available")
        
        try:
            # Define the style for the prompt
            style = Style.from_dict({
                'prompt': 'bold green',
                'input': 'white',
            })
            
            # Create a simple completer for commands
            command_completer = WordCompleter(self.commands, ignore_case=True)
            
            while True:
                try:
                    # Use a custom input hook to detect forward slash
                    user_input = self.session.prompt(
                        HTML('<b><style fg="green">You</style></b>: '),
                        completer=command_completer,
                        complete_style=CompleteStyle.MULTI_COLUMN,
                        style=style,
                        enable_history_search=True,
                        vi_mode=True  # Enable vi editing mode
                    )
                    
                    # Check if it's a special result from key bindings
                    if user_input == '/help_popup':
                        self._show_command_popup()
                        continue
                    elif user_input == '__keyboard_interrupt__':
                        raise KeyboardInterrupt
                    elif user_input == '__eof__':
                        return 'exit'
                    
                    return user_input
                    
                except KeyboardInterrupt:
                    return 'exit'
                except EOFError:
                    return 'exit'
                    
        except Exception as e:
            self.console.print(f"[yellow]Warning: Falling back to basic input due to error: {e}[/yellow]")
            return self._get_input_fallback()

    def _get_input_fallback(self) -> str:
        """Fallback input method for better compatibility."""
        # Try different methods based on platform
        if sys.platform == "win32":
            return self._get_input_windows_basic()
        else:
            return self._get_input_unix_basic()

    def _get_input_windows_basic(self) -> str:
        """Basic input for Windows systems."""
        try:
            # For basic compatibility, use regular input
            self.console.print("[bold green]You[/bold green]: ", end="", flush=True)
            return input()
        except (KeyboardInterrupt, EOFError):
            return 'exit'

    def _get_input_unix_basic(self) -> str:
        """Basic input for Unix systems."""
        try:
            # For basic compatibility, use regular input
            self.console.print("[bold green]You[/bold green]: ", end="", flush=True)
            return input()
        except (KeyboardInterrupt, EOFError):
            return 'exit'

    def get_input_with_features(self) -> str:
        """Get user input with slash detection and auto-completion."""
        try:
            if HAS_PROMPT_TOOLKIT:
                return self._get_input_prompt_toolkit()
            else:
                return self._get_input_fallback()
        except Exception as e:
            # If all enhanced methods fail, fall back to standard input
            self.console.print(f"[red]Error in enhanced input, using standard input: {e}[/red]")
            try:
                self.console.print("[bold green]You[/bold green]: ", end="", flush=True)
                return input()
            except (KeyboardInterrupt, EOFError):
                return 'exit'

    def register_command(self, command: str, description: str):
        """Register a new command with its description."""
        if command not in self.commands:
            self.commands.append(command)
            self.command_descriptions[command] = description

    def show_help(self):
        """Show help using Rich formatting if available."""
        return self._show_command_popup()


def detect_terminal_capabilities() -> Dict[str, bool]:
    """Detect terminal capabilities for compatibility."""
    capabilities = {
        'prompt_toolkit': HAS_PROMPT_TOOLKIT,
        'colors': True,  # Assume colors are supported
        'unicode': True,  # Assume Unicode is supported
        'cursor_control': True  # Assume cursor control is supported
    }
    
    # Try to detect actual terminal capabilities
    try:
        # Check if we're in a real terminal
        is_tty = sys.stdin.isatty()
        capabilities['tty'] = is_tty
        
        # Check terminal size
        import shutil
        terminal_size = shutil.get_terminal_size()
        capabilities['width'] = terminal_size.columns
        capabilities['height'] = terminal_size.lines
    except:
        # If detection fails, use defaults
        capabilities['tty'] = True
        capabilities['width'] = 80
        capabilities['height'] = 24
    
    return capabilities