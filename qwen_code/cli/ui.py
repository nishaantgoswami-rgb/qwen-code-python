"""Enhanced UI components for Qwen Code CLI with syntax highlighting, code folding, and themes."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.tree import Tree
from rich.style import Style
from rich.color import Color

console = Console()

@dataclass
class Theme:
    """Color theme definition for the CLI interface."""
    name: str
    primary: str = "blue"
    secondary: str = "cyan"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "magenta"
    user_input: str = "green"
    ai_response: str = "blue"
    highlight: str = "bright_yellow"
    background: str = "#2e2e2e"
    panel_border: str = "blue"
    code_background: str = "#1e1e1e"

THEMES = {
    "default": Theme(
        name="default",
        primary="blue",
        secondary="cyan",
        success="green",
        warning="yellow", 
        error="red",
        info="magenta",
        user_input="green",
        ai_response="blue",
        highlight="bright_yellow"
    ),
    "dark": Theme(
        name="dark",
        primary="#8be9fd",
        secondary="#bd93f9", 
        success="#50fa7b",
        warning="#f1fa8c",
        error="#ff5555",
        info="#ff79c6",
        user_input="#50fa7b",
        ai_response="#8be9fd",
        highlight="#ffb86c",
        background="#282a36",
        panel_border="#44475a",
        code_background="#21222c"
    ),
    "light": Theme(
        name="light",
        primary="#0066cc",
        secondary="#008080",
        success="#00aa00", 
        warning="#cc6600",
        error="#cc0000",
        info="#9900cc",
        user_input="#008000",
        ai_response="#0066cc",
        highlight="#ff6600",
        background="#ffffff",
        panel_border="#cccccc",
        code_background="#f5f5f5"
    ),
    "high_contrast": Theme(
        name="high_contrast",
        primary="#0000ff",
        secondary="#00ffff",
        success="#00ff00",
        warning="#ffff00",
        error="#ff0000", 
        info="#ff00ff",
        user_input="#00ff00",
        ai_response="#0000ff",
        highlight="#ffff00",
        background="#000000",
        panel_border="#ffffff",
        code_background="#111111"
    )
}

class EnhancedUI:
    """Enhanced UI components with themes, syntax highlighting, and code folding."""
    
    def __init__(self, theme_name: str = "default"):
        self.theme = THEMES.get(theme_name, THEMES["default"])
        self.console = Console()
        
    def set_theme(self, theme_name: str):
        """Change the current theme."""
        self.theme = THEMES.get(theme_name, THEMES["default"])
        
    def print_welcome(self):
        """Display welcome message with enhanced formatting."""
        title = """
  Qwen Code
  =========
        """
        title_panel = Panel(
            f"[bold]{title}[/bold]\n\n"
            f"[bold {self.theme.primary}]Qwen Code[/bold {self.theme.primary}] - AI-powered coding assistant\n"
            f"[{self.theme.secondary}]Model:[/{self.theme.secondary}] qwen3-coder-plus\n"
            f"[{self.theme.secondary}]Type:[/{self.theme.secondary}] [bold {self.theme.success}]'exit'[/bold {self.theme.success}] or [bold {self.theme.success}]'quit'[/bold {self.theme.success}] to end the session\n"
            f"[{self.theme.secondary}]Type:[/{self.theme.secondary}] [bold {self.theme.success}]'/help'[/bold {self.theme.success}] for available commands\n"
            f"[{self.theme.secondary}]Press:[/{self.theme.secondary}] [bold {self.theme.success}]'/'[/bold {self.theme.success}] at any time to see available commands\n"
            f"[{self.theme.secondary}]Press:[/{self.theme.secondary}] [bold {self.theme.success}]Tab[/bold {self.theme.success}] for auto-completion",
            title="Welcome",
            border_style=self.theme.panel_border,
            expand=False
        )
        self.console.print(title_panel)
        
    def print_ai_response(self, content: str):
        """Print AI response with syntax highlighting, code folding, and markdown formatting."""
        # Create a group to hold all the content
        content_group = Group()
        
        # If content contains markdown with code blocks, process it specially
        if '```' in content:
            # Split the content by code blocks
            parts = content.split('```')
            in_code_block = False
            
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Odd indices are code blocks
                    # This is a code block - extract language if specified
                    lines = part.strip().split('\n', 1)
                    lang = 'text'
                    code_content = part
                    
                    if len(lines) > 1 and lines[0].strip() in ['python', 'javascript', 'java', 'c++', 'cpp', 'c', 'html', 'css', 'json', 'yaml', 'bash', 'sql', 'go', 'rust', 'typescript', 'yaml', 'xml', 'php', 'ruby', 'swift', 'kotlin', 'scala']:
                        lang = lines[0].strip()
                        code_content = lines[1] if len(lines) > 1 else ''
                    
                    # Create a collapsible code block panel with syntax highlighting
                    code_syntax = Syntax(
                        code_content, 
                        lang, 
                        theme="monokai" if self.theme.name != "light" else "default",
                        line_numbers=True,
                        code_width=80,
                        background_color=self.theme.code_background,
                        word_wrap=True
                    )
                    
                    # For very long code blocks, provide folding functionality
                    lines_count = len(code_content.split('\n'))
                    title = f"Code: {lang}"
                    if lines_count > 20:
                        title += f" ({lines_count} lines) [dim][Press 'c' to collapse/expand][/dim]"
                    
                    code_panel = Panel(
                        code_syntax,
                        title=title,
                        border_style=self.theme.secondary,
                        expand=True
                    )
                    content_group.renderables.append(code_panel)
                    
                    # Add a separator after long code blocks
                    if lines_count > 20:
                        content_group.renderables.append(Text("\n"))
                else:
                    # Regular markdown content
                    if part.strip():
                        md = Markdown(part)
                        content_group.renderables.append(md)
        else:
            # Regular markdown content
            md = Markdown(content)
            content_group.renderables.append(md)
            
        # Print the AI response with styling
        self.console.print(f"[bold {self.theme.ai_response}]AI Response:[/bold {self.theme.ai_response}]")
        self.console.print(content_group)
        self.console.print()  # Empty line for readability
        
    def print_user_input(self, content: str):
        """Print user input with styling."""
        self.console.print(f"[bold {self.theme.user_input}]>You:[/bold {self.theme.user_input}] {content}")
        
    def show_thinking_indicator(self, description: str = "Thinking..."):
        """Show a thinking indicator with spinner."""
        from rich.live import Live
        from time import sleep

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )
        
        task_id = progress.add_task(f"[{self.theme.secondary}]{description}...", total=None)
        
        # Return the progress object and task_id so it can be managed externally
        return progress, task_id

    def show_help(self):
        """Show enhanced help with table formatting."""
        help_table = Table(
            title="Available Commands",
            show_header=True, 
            header_style=f"bold {self.theme.info}",
            border_style=self.theme.panel_border
        )
        help_table.add_column("Command", style=self.theme.primary, width=15)
        help_table.add_column("Description", style="white")
        
        help_table.add_row("/help", "Show this help message")
        help_table.add_row("/clear", "Clear conversation history")
        help_table.add_row("/stats", "Show conversation statistics")
        help_table.add_row("/status", "Show session status")
        help_table.add_row("/auth", "Manage authentication")
        help_table.add_row("/config", "Manage configuration")
        help_table.add_row("/quit", "Exit the session")
        help_table.add_row("/theme [name]", "Change UI theme")
        
        self.console.print(help_table)
        self.console.print(f"[{self.theme.info}]Tips:[/{self.theme.info}]")
        self.console.print(f"  • Press [bold {self.theme.success}]'/'[/bold {self.theme.success}] at any time to see available commands")
        self.console.print(f"  • Press [bold {self.theme.success}]Tab[/bold {self.theme.success}] for auto-completion of commands")
        self.console.print(f"  • Available themes: {', '.join(THEMES.keys())}")
        
    def show_stats(self, messages: List[Any]):
        """Show conversation statistics."""
        user_messages = sum(1 for msg in messages if hasattr(msg, 'role') and msg.role == "user")
        assistant_messages = sum(1 for msg in messages if hasattr(msg, 'role') and msg.role == "assistant")
        
        stats_table = Table(
            title="Conversation Statistics", 
            show_header=True, 
            header_style=f"bold {self.theme.info}",
            border_style=self.theme.panel_border
        )
        stats_table.add_column("Metric", style=self.theme.primary)
        stats_table.add_column("Value", style="white")
        
        stats_table.add_row("Total messages", str(len(messages)))
        stats_table.add_row("Your messages", str(user_messages))
        stats_table.add_row("AI responses", str(assistant_messages))
        
        self.console.print(stats_table)
        
    def show_themes(self):
        """Show available themes."""
        theme_table = Table(
            title="Available Themes",
            show_header=True,
            header_style=f"bold {self.theme.info}",
            border_style=self.theme.panel_border
        )
        theme_table.add_column("Name", style=self.theme.primary)
        theme_table.add_column("Description", style="white")
        
        theme_table.add_row("default", "Standard blue-themed interface")
        theme_table.add_row("dark", "Dark theme with vibrant colors")
        theme_table.add_row("light", "Light theme for bright environments") 
        theme_table.add_row("high_contrast", "High contrast for accessibility")
        
        self.console.print(theme_table)
        self.console.print(f"[{self.theme.info}]Current theme:[/{self.theme.info}] [bold]{self.theme.name}[/bold]")
        
    def print_error(self, message: str):
        """Print error message with styling."""
        self.console.print(f"[bold {self.theme.error}]ERROR:[/bold {self.theme.error}] {message}")
        
    def print_success(self, message: str):
        """Print success message with styling."""
        self.console.print(f"[bold {self.theme.success}]SUCCESS:[/bold {self.theme.success}] {message}")
        
    def print_warning(self, message: str):
        """Print warning message with styling."""
        self.console.print(f"[bold {self.theme.warning}]WARNING:[/bold {self.theme.warning}] {message}")
        
    def print_info(self, message: str):
        """Print info message with styling."""
        self.console.print(f"[bold {self.theme.info}]INFO:[/bold {self.theme.info}] {message}")
        
    def create_collapsible_code_block(self, code: str, language: str = "python", title: str = "Code"):
        """Create a collapsible code block panel."""
        syntax = Syntax(
            code, 
            language, 
            theme="monokai" if self.theme.name != "light" else "default",
            line_numbers=True,
            background_color=self.theme.code_background
        )
        
        panel = Panel(
            syntax,
            title=title,
            border_style=self.theme.secondary,
            expand=True
        )
        return panel
    
    def show_status(self):
        """Show session status information."""
        from datetime import datetime
        
        status_table = Table(
            title="Session Status", 
            show_header=True, 
            header_style=f"bold {self.theme.info}",
            border_style=self.theme.panel_border
        )
        status_table.add_column("Property", style=self.theme.primary)
        status_table.add_column("Value", style="white")
        
        status_table.add_row("Status", "Active")
        status_table.add_row("Model", "qwen3-coder-plus")
        status_table.add_row("Created", str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        status_table.add_row("Last Activity", str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        status_table.add_row("Theme", self.theme.name)
        
        self.console.print(status_table)