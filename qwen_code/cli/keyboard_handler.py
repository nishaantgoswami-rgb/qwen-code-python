"""Keyboard handling utilities for the Qwen Code CLI."""

import sys
from rich.console import Console

try:
    import msvcrt  # Windows
except ImportError:
    try:
        import tty, termios  # Unix/Linux
    except ImportError:
        pass

console = Console()


class KeyboardHandler:
    """Handles keyboard input with special key detection."""
    
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
    
    def get_input_with_features(self) -> str:
        """Get user input with slash detection and auto-completion."""
        try:
            if sys.platform == "win32":
                return self._get_input_windows()
            else:
                return self._get_input_unix()
        except Exception:
            # Fallback to standard input if enhanced input fails
            console.print("[bold green]You[/bold green]: ", end="", markup=True)
            user_input = input()
            return user_input
    
    def _get_input_windows(self) -> str:
        """Handle input on Windows with enhanced features."""
        console.print("[bold green]You[/bold green]: ", end="", markup=True)
        user_input = ""
        
        while True:
            if msvcrt.kbhit():
                try:
                    key = msvcrt.getch()
                    # Handle special keys that might not decode properly
                    if hasattr(key, 'decode'):
                        try:
                            key = key.decode('utf-8')
                        except UnicodeDecodeError:
                            # Skip non-decodable keys
                            continue
                    else:
                        key = ''
                except Exception:
                    # If we can't process the key, continue
                    continue
                
                # Handle special keys
                if key == '\r':  # Enter key
                    print()  # New line
                    break
                elif key == '\x08':  # Backspace
                    if len(user_input) > 0:
                        user_input = user_input[:-1]
                        print("\b \b", end="", flush=True)  # Erase last character
                elif key == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                elif key == '/':  # Forward slash
                    user_input += key
                    print(key, end="", flush=True)
                    # Show help immediately
                    self._show_help_inline()
                    # Continue accepting input
                elif key == '\t':  # Tab key for auto-completion
                    if user_input.startswith('/'):
                        completed_command = self._auto_complete_command(user_input)
                        if completed_command and completed_command != user_input:
                            # Clear current input and replace with completed command
                            for _ in range(len(user_input)):
                                print("\b \b", end="")
                            user_input = completed_command
                            print(user_input, end="", flush=True)
                else:
                    user_input += key
                    print(key, end="", flush=True)
        
        return user_input
    
    def _get_input_unix(self) -> str:
        """Handle input on Unix/Linux with enhanced features."""
        console.print("[bold green]You[/bold green]: ", end="", markup=True)
        user_input = ""
        
        # Save terminal settings
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
        except:
            # If we can't get terminal settings, fall back to regular input
            print()  # New line
            return input()
        
        try:
            # Set terminal to non-canonical mode
            tty.setraw(sys.stdin.fileno())
            
            while True:
                key = sys.stdin.read(1)
                
                # Handle special keys based on ASCII values
                if ord(key) == 13:  # Enter key
                    print()  # New line
                    break
                elif ord(key) == 127:  # Backspace
                    if len(user_input) > 0:
                        user_input = user_input[:-1]
                        print("\b \b", end="", flush=True)  # Erase last character
                elif ord(key) == 3:  # Ctrl+C
                    raise KeyboardInterrupt
                elif key == '/':  # Forward slash
                    user_input += key
                    print(key, end="", flush=True)
                    # Show help immediately
                    self._show_help_inline()
                    # Continue accepting input
                elif ord(key) == 9:  # Tab key for auto-completion
                    if user_input.startswith('/'):
                        completed_command = self._auto_complete_command(user_input)
                        if completed_command and completed_command != user_input:
                            # Clear current input and replace with completed command
                            for _ in range(len(user_input)):
                                print("\b \b", end="")
                            user_input = completed_command
                            print(user_input, end="", flush=True)
                else:
                    user_input += key
                    print(key, end="", flush=True)
        except Exception:
            # If we encounter any issues, restore settings and re-raise
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            raise
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        return user_input
    
    def _show_help_inline(self) -> None:
        """Show available commands inline without interrupting the input flow."""
        # Print a new line and show help
        print()
        
        # Show help in a compact format
        console.print("[bold cyan]Available Commands:[/bold cyan]")
        for command in self.commands:
            desc = self.command_descriptions.get(command, "")
            console.print(f"  [green]{command:<10}[/green] - {desc}")
        
        console.print("[blue]Tip:[/blue] Press [green]Tab[/green] for auto-completion")
        
        # Show prompt again using Rich
        console.print("[bold green]You[/bold green]: ", end="", markup=True)
    
    def _auto_complete_command(self, partial_input: str) -> str:
        """Auto-complete command based on partial input."""
        if not partial_input.startswith('/'):
            return partial_input
        
        # Get the command part after the slash
        cmd_part = partial_input[1:]  # Remove the leading slash
        
        # Find exact match first
        exact_matches = [cmd for cmd in self.commands if cmd == '/' + cmd_part]
        if exact_matches:
            return exact_matches[0]
        
        # Find matching commands
        matches = [cmd for cmd in self.commands if cmd.startswith('/' + cmd_part)]
        
        if len(matches) == 1:
            # Single match found
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches, find the longest common prefix
            prefix = self._longest_common_prefix(matches)
            if prefix and len(prefix) > len(partial_input):
                return prefix
            else:
                # Show options if no common prefix extension
                print()
                console.print("[bold yellow]Possible completions:[/bold yellow]")
                for match in matches:
                    console.print(f"  {match}")
                console.print(f"[bold green]You[/bold green]: {partial_input}", end="", markup=True)
        
        # Return original input if no single match or no extension
        return partial_input
    
    def _longest_common_prefix(self, strs: list) -> str:
        """Find the longest common prefix among a list of strings."""
        if not strs:
            return ""
        
        # Sort the strings to compare first and last
        strs_sorted = sorted(strs)
        first = strs_sorted[0]
        last = strs_sorted[-1]
        
        # Find common prefix between first and last
        prefix = ""
        for i in range(min(len(first), len(last))):
            if first[i] == last[i]:
                prefix += first[i]
            else:
                break
        
        return prefix