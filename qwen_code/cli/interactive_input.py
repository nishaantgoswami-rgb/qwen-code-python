"""Interactive input handling with slash command completion for Qwen Code CLI."""

import sys
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
from rich.console import Console

console = Console()

try:
    import tty
    import termios
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False
    tty = None
    termios = None

try:
    import msvcrt  # Windows
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False
    msvcrt = None

class CompletionMode(Enum):
    IDLE = "IDLE"
    SLASH = "SLASH"

@dataclass
class Command:
    name: str
    description: str
    action: Optional[callable] = None
    alt_names: List[str] = None

    def __post_init__(self):
        if self.alt_names is None:
            self.alt_names = []

@dataclass
class Suggestion:
    label: str
    value: str
    description: str = ""

class SlashCommandCompletion:
    def __init__(self, commands: List[Command]):
        self.commands = commands
        self.suggestions: List[Suggestion] = []
        self.active_index = 0
        self.show_suggestions = False
        
    def get_matching_commands(self, query: str) -> List[Suggestion]:
        """Filter commands based on query and return as suggestions."""
        if not query.startswith('/'):
            return []
        
        # Remove the leading slash and any trailing space
        search_term = query[1:].rstrip()
        
        matching = []
        for cmd in self.commands:
            # Check if command name or alt names match
            if (cmd.name.startswith(search_term) or 
                any(alt.startswith(search_term) for alt in cmd.alt_names if alt)):
                matching.append(Suggestion(
                    label=cmd.name,
                    value=cmd.name,
                    description=cmd.description
                ))
        
        return matching
    
    def update_suggestions(self, query: str):
        """Update suggestions based on current query."""
        self.suggestions = self.get_matching_commands(query)
        self.show_suggestions = len(self.suggestions) > 0
        self.active_index = 0 if self.suggestions else -1
    
    def navigate_up(self):
        """Navigate up in suggestions list."""
        if self.suggestions and self.active_index > 0:
            self.active_index -= 1
    
    def navigate_down(self):
        """Navigate down in suggestions list."""
        if self.suggestions and self.active_index < len(self.suggestions) - 1:
            self.active_index += 1
    
    def get_active_suggestion(self) -> Optional[Suggestion]:
        """Get the currently active suggestion."""
        if self.suggestions and 0 <= self.active_index < len(self.suggestions):
            return self.suggestions[self.active_index]
        return None

class InteractiveInput:
    def __init__(self, commands: List[Command]):
        self.completion = SlashCommandCompletion(commands)
        self.buffer = ""
        self.cursor_pos = 0
        self._prev_suggestions_count = 0
        
    def render_input_line(self):
        """Render the current input line with cursor."""
        # Clear current line and move cursor to beginning
        sys.stdout.write('\r\033[K')
        
        # Render prompt
        sys.stdout.write('> ')
        
        # Render buffer with cursor
        if self.cursor_pos < len(self.buffer):
            before_cursor = self.buffer[:self.cursor_pos]
            at_cursor = self.buffer[self.cursor_pos]
            after_cursor = self.buffer[self.cursor_pos + 1:]
            sys.stdout.write(f"{before_cursor}\033[7m{at_cursor}\033[0m{after_cursor}")
        else:
            sys.stdout.write(self.buffer)
            sys.stdout.write('\033[7m \033[0m')  # Show cursor at end
        
        sys.stdout.flush()
    
    def render_suggestions(self):
        """Render the suggestions dropdown."""
        if not self.completion.show_suggestions:
            # If suggestions should not be shown, make sure to clear any existing ones
            if hasattr(self, '_prev_suggestions_count') and self._prev_suggestions_count > 0:
                # Clear the display area where suggestions were shown
                for i in range(self._prev_suggestions_count):
                    sys.stdout.write('\n\033[K')
                # Move cursor back up
                sys.stdout.write(f'\033[{self._prev_suggestions_count}A')
                sys.stdout.flush()
            return
        
        # Clear the previous suggestion lines if any existed
        if hasattr(self, '_prev_suggestions_count') and self._prev_suggestions_count > 0:
            # Clear the old suggestions by overwriting them
            for i in range(self._prev_suggestions_count):
                sys.stdout.write('\n\033[K')
            # Move cursor back to where those lines were
            sys.stdout.write(f'\033[{self._prev_suggestions_count}A')
        
        # Render the current suggestions
        for i, suggestion in enumerate(self.completion.suggestions):
            sys.stdout.write('\n')
            
            if i == self.completion.active_index:
                # Highlight active suggestion
                sys.stdout.write(f'\033[44m\033[37m  /{suggestion.label}\033[0m')
                if suggestion.description:
                    sys.stdout.write(f' - {suggestion.description}')
            else:
                sys.stdout.write(f'  /{suggestion.label}')
                if suggestion.description:
                    sys.stdout.write(f' - {suggestion.description}')
        
        # Update the previous suggestions count for next render
        self._prev_suggestions_count = len(self.completion.suggestions)
        
        # Move cursor back to input line
        if self.completion.suggestions:
            sys.stdout.write(f'\033[{len(self.completion.suggestions)}A')
        
        sys.stdout.flush()
    
    def clear_suggestions_display(self):
        """Clear the suggestions from display."""
        if self.completion.show_suggestions:
            # Move down to clear suggestion lines
            for i in range(len(self.completion.suggestions)):
                sys.stdout.write('\n\033[K')
            # Move back up
            if self.completion.suggestions:
                sys.stdout.write(f'\033[{len(self.completion.suggestions)}A')
            sys.stdout.flush()
    
    def handle_key_input(self, key: str) -> Optional[str]:
        """Handle keyboard input and return completed command if any."""
        if key == '\x03':  # Ctrl+C
            raise KeyboardInterrupt
        
        elif key == '\x04':  # Ctrl+D (EOF)
            if not self.buffer:
                raise EOFError
        
        elif key == '\r' or key == '\n':  # Enter
            if self.completion.show_suggestions and self.completion.active_index >= 0:
                # Auto-complete with selected suggestion
                suggestion = self.completion.get_active_suggestion()
                if suggestion:
                    self.buffer = f'/{suggestion.value} '
                    self.cursor_pos = len(self.buffer)
                    self.completion.show_suggestions = False
                    return None
            else:
                # Submit the current buffer
                result = self.buffer.strip()
                self.buffer = ""
                self.cursor_pos = 0
                self.completion.show_suggestions = False
                return result
        
        elif key == '\t':  # Tab - autocomplete
            if self.completion.show_suggestions and self.completion.active_index >= 0:
                suggestion = self.completion.get_active_suggestion()
                if suggestion:
                    self.buffer = f'/{suggestion.value} '
                    self.cursor_pos = len(self.buffer)
                    self.completion.show_suggestions = False
        
        # Handle arrow keys (Unix and Windows)
        elif key == '\x1b[A' or key == 'UP':  # Up arrow (Unix: \x1b[A, Windows: UP)
            if self.completion.show_suggestions:
                self.completion.navigate_up()
            return None
        
        elif key == '\x1b[B' or key == 'DOWN':  # Down arrow (Unix: \x1b[B, Windows: DOWN)
            if self.completion.show_suggestions:
                self.completion.navigate_down()
            return None
        
        elif key == '\x7f' or key == '\b':  # Backspace
            if self.cursor_pos > 0:
                self.buffer = self.buffer[:self.cursor_pos-1] + self.buffer[self.cursor_pos:]
                self.cursor_pos -= 1
                self.completion.update_suggestions(self.buffer)
        
        elif key == '\x1b[D' or key == 'LEFT':  # Left arrow (Unix: \x1b[D, Windows: LEFT)
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
        
        elif key == '\x1b[C' or key == 'RIGHT':  # Right arrow (Unix: \x1b[C, Windows: RIGHT)
            if self.cursor_pos < len(self.buffer):
                self.cursor_pos += 1
        
        elif key.isprintable():
            # Regular character input
            self.buffer = self.buffer[:self.cursor_pos] + key + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
            
            # Update suggestions if we're typing a slash command
            self.completion.update_suggestions(self.buffer)
        
        return None
    
    def read_key(self) -> str:
        """Read a single key from stdin."""
        if sys.platform == "win32":
            return self._read_key_windows()
        else:
            return self._read_key_unix()

    def _read_key_unix(self) -> str:
        """Read a single key from stdin on Unix systems."""
        if not HAS_TERMIOS:
            # Fallback for systems without termios
            return input()
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            
            # Handle escape sequences (arrow keys, etc.)
            if key == '\x1b':
                key += sys.stdin.read(2)
            
            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _read_key_windows(self) -> str:
        """Read a single key from stdin on Windows."""
        if not HAS_MSVCRT:
            # Fallback for systems without msvcrt
            return input()
        
        key = msvcrt.getch()
        
        # Check if it's a special key (arrow keys, function keys, etc.)
        if ord(key) == 0 or ord(key) == 224:
            # Extended key, get the second character - return specific values for arrow keys
            next_key = msvcrt.getch()
            if ord(next_key) == 72:  # Up arrow
                return 'UP'
            elif ord(next_key) == 80:  # Down arrow
                return 'DOWN'
            elif ord(next_key) == 75:  # Left arrow
                return 'LEFT'
            elif ord(next_key) == 77:  # Right arrow
                return 'RIGHT'
            else:
                # For other extended keys, return a special marker
                return f'EXT:{ord(next_key)}'
        
        return key.decode('utf-8', errors='ignore')
    
    def run(self) -> str:
        """Main input loop."""
        print("Qwen Code CLI - Type / to see available commands")
        
        while True:
            self.render_input_line()
            self.render_suggestions()
            
            try:
                key = self.read_key()
                result = self.handle_key_input(key)
                
                if result is not None:
                    self.clear_suggestions_display()
                    return result
                    
            except (KeyboardInterrupt, EOFError):
                self.clear_suggestions_display()
                print("\nGoodbye!")
                sys.exit(0)

# Example usage
def main():
    # Define available commands (same as Qwen Code CLI)
    commands = [
        Command("help", "Display available commands"),
        Command("clear", "Clear conversation history"),
        Command("compress", "Compress history to save tokens"),
        Command("stats", "Show current session information"),
        Command("exit", "Exit Qwen Code", alt_names=["quit"]),
        Command("auth", "Authentication management"),
        Command("session", "Session management"),
        Command("config", "Configuration management"),
    ]
    
    interactive_input = InteractiveInput(commands)
    
    while True:
        try:
            user_input = interactive_input.run()
            print(f"\nYou entered: {user_input}")
            
            # Handle the command
            if user_input.startswith('/'):
                cmd_name = user_input[1:].split()[0]
                print(f"Executing command: {cmd_name}")
                
                if cmd_name in ['exit', 'quit']:
                    break
            else:
                print("Regular chat input - sending to AI...")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()