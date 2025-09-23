"""
Enhanced parser optimized for Qwen-Coder models.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class CodeBlockType(Enum):
    """Types of code blocks."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    MARKDOWN = "markdown"
    YAML = "yaml"
    JSON = "json"
    SHELL = "shell"
    TEXT = "text"
    OTHER = "other"


@dataclass
class CodeBlock:
    """Represents a code block in AI response."""
    language: str
    code: str
    filename: Optional[str] = None
    start_line: Optional[int] = None
    block_type: CodeBlockType = CodeBlockType.OTHER


@dataclass
class FileOperation:
    """Represents a file operation command."""
    operation: str  # "create", "modify", "delete", "read"
    path: str
    content: Optional[str] = None
    language: Optional[str] = None


@dataclass
class Command:
    """Represents an executable command."""
    command: str
    description: Optional[str] = None


class QwenParser:
    """Enhanced parser optimized for Qwen-Coder models."""
    
    def __init__(self):
        # Regex patterns for parsing
        self.code_block_pattern = re.compile(
            r"```(?P<language>[a-zA-Z#+]*)\s*\n(?P<code>.*?)\s*```", 
            re.DOTALL
        )
        self.filename_pattern = re.compile(
            r"^(?:filename:\s*)?(?:\*\*)?(?P<filename>[\w\-./\\]+\.[\w]+)(?:\*\*)?",
            re.IGNORECASE
        )
        self.file_op_pattern = re.compile(
            r"(?:^|\n)(?P<operation>Create|Modify|Delete|Read)\s+file\s*:\s*(?P<path>[\w\-./\\]+\.[\w]+)",
            re.IGNORECASE
        )
        self.command_pattern = re.compile(
            r"```(?:bash|shell|sh)\s*\n(?P<command>.*?)\s*```",
            re.DOTALL
        )
    
    def parse_code_blocks(self, content: str) -> List[CodeBlock]:
        """Extract and parse code blocks from AI response."""
        code_blocks = []
        
        # Find all code blocks
        for match in self.code_block_pattern.finditer(content):
            language = match.group("language") or "text"
            code = match.group("code").strip()
            
            # Try to extract filename from the code block or preceding text
            filename = None
            start_pos = match.start()
            # Look for filename in the 200 characters before the code block
            preceding_text = content[max(0, start_pos - 200):start_pos]
            filename_match = self.filename_pattern.search(preceding_text)
            if filename_match:
                filename = filename_match.group("filename")
            
            # If no filename found, try to find it in the first line of the code block
            if not filename and code:
                first_line = code.split('\n')[0]
                filename_match = self.filename_pattern.search(first_line)
                if filename_match:
                    filename = filename_match.group("filename")
            
            code_blocks.append(CodeBlock(
                language=language,
                code=code,
                filename=filename,
                block_type=self._get_block_type(language)
            ))
        
        return code_blocks
    
    def parse_file_operations(self, content: str) -> List[FileOperation]:
        """Parse file operation commands from AI response."""
        operations = []
        
        # Find all file operations
        for match in self.file_op_pattern.finditer(content):
            operation = match.group("operation").lower()
            path = match.group("path")
            
            # Try to find associated content
            content_match = self._find_associated_content(content, match.end())
            
            operations.append(FileOperation(
                operation=operation,
                path=path,
                content=content_match.code if content_match else None,
                language=content_match.language if content_match else None
            ))
        
        return operations
    
    def extract_commands(self, content: str) -> List[Command]:
        """Extract executable commands from AI response."""
        commands = []
        
        # Find all command blocks
        for match in self.command_pattern.finditer(content):
            command_text = match.group("command").strip()
            # Split multiple commands separated by newlines
            for cmd in command_text.split('\n'):
                cmd = cmd.strip()
                if cmd:
                    commands.append(Command(command=cmd))
        
        return commands
    
    def _get_block_type(self, language: str) -> CodeBlockType:
        """Convert language string to CodeBlockType enum."""
        language_map = {
            'py': CodeBlockType.PYTHON,
            'python': CodeBlockType.PYTHON,
            'js': CodeBlockType.JAVASCRIPT,
            'javascript': CodeBlockType.JAVASCRIPT,
            'ts': CodeBlockType.TYPESCRIPT,
            'typescript': CodeBlockType.TYPESCRIPT,
            'java': CodeBlockType.JAVA,
            'cpp': CodeBlockType.CPP,
            'c++': CodeBlockType.CPP,
            'c': CodeBlockType.C,
            'cs': CodeBlockType.CSHARP,
            'c#': CodeBlockType.CSHARP,
            'go': CodeBlockType.GO,
            'golang': CodeBlockType.GO,
            'rs': CodeBlockType.RUST,
            'rust': CodeBlockType.RUST,
            'rb': CodeBlockType.RUBY,
            'ruby': CodeBlockType.RUBY,
            'php': CodeBlockType.PHP,
            'swift': CodeBlockType.SWIFT,
            'sql': CodeBlockType.SQL,
            'html': CodeBlockType.HTML,
            'css': CodeBlockType.CSS,
            'md': CodeBlockType.MARKDOWN,
            'markdown': CodeBlockType.MARKDOWN,
            'yaml': CodeBlockType.YAML,
            'yml': CodeBlockType.YAML,
            'json': CodeBlockType.JSON,
            'sh': CodeBlockType.SHELL,
            'bash': CodeBlockType.SHELL,
            'shell': CodeBlockType.SHELL,
        }
        
        lang_lower = language.lower()
        if lang_lower in language_map:
            return language_map[lang_lower]
        return CodeBlockType.OTHER
    
    def _find_associated_content(self, content: str, start_pos: int) -> Optional[CodeBlock]:
        """Find code content associated with a file operation."""
        # Look for code blocks after the file operation
        remaining_content = content[start_pos:]
        
        # Find the first code block
        match = self.code_block_pattern.search(remaining_content)
        if match:
            language = match.group("language") or "text"
            code = match.group("code").strip()
            return CodeBlock(language=language, code=code)
        
        return None
    
    def parse_all(self, content: str) -> Dict[str, List[Any]]:
        """Parse all elements from AI response."""
        return {
            "code_blocks": self.parse_code_blocks(content),
            "file_operations": self.parse_file_operations(content),
            "commands": self.extract_commands(content)
        }