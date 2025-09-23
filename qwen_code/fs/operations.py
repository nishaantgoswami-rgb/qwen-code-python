"""
File system operations for Qwen Code.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import hashlib
import fnmatch
from datetime import datetime
import asyncio


@dataclass
class CodebaseAnalysis:
    """Results of codebase analysis."""
    total_files: int = 0
    total_lines: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    structure: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileMetadata:
    """File metadata model."""
    file_path: str
    project_path: str
    file_type: str
    size_bytes: int
    lines_count: int
    last_modified: datetime
    content_hash: str
    analysis_data: Dict[str, Any] = field(default_factory=dict)


class FileManager:
    """Handles file system operations for code analysis and modification."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    async def read_file(self, path: Path) -> str:
        """Read file content safely."""
        full_path = self.project_root / path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise FileNotFoundError(f"Could not read file {full_path}: {str(e)}")
    
    async def write_file(self, path: Path, content: str) -> None:
        """Write content to file with backup."""
        full_path = self.project_root / path
        # Create backup if file exists
        if full_path.exists():
            backup_path = full_path.with_suffix(full_path.suffix + '.backup')
            full_path.rename(backup_path)
        
        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write new content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    async def analyze_codebase(self, include_patterns: List[str] = None, 
                              exclude_patterns: List[str] = None) -> CodebaseAnalysis:
        """Analyze project structure and dependencies."""
        analysis = CodebaseAnalysis()
        
        # Default patterns if not provided
        if include_patterns is None:
            include_patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.java", "**/*.cpp", "**/*.c"]
        if exclude_patterns is None:
            exclude_patterns = [".git/**", "__pycache__/**", "node_modules/**", "*.pyc"]
        
        # Get all files matching patterns
        files = self.get_project_files(include_patterns, exclude_patterns)
        
        # Analyze each file
        for file_path in files:
            try:
                full_path = self.project_root / file_path
                # Get file stats
                stat = full_path.stat()
                
                # Count lines and detect language
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                lines_count = len(lines)
                analysis.total_files += 1
                analysis.total_lines += lines_count
                
                # Simple language detection by extension
                ext = file_path.suffix.lower()
                lang = {
                    '.py': 'Python',
                    '.js': 'JavaScript',
                    '.ts': 'TypeScript',
                    '.java': 'Java',
                    '.cpp': 'C++',
                    '.c': 'C',
                    '.cs': 'C#',
                    '.go': 'Go',
                    '.rs': 'Rust',
                    '.rb': 'Ruby',
                    '.php': 'PHP',
                    '.swift': 'Swift'
                }.get(ext, 'Other')
                
                analysis.languages[lang] = analysis.languages.get(lang, 0) + 1
                
                # Simple dependency detection for Python files
                if ext == '.py':
                    for line in lines:
                        if line.startswith('import ') or line.startswith('from '):
                            # Extract module name
                            parts = line.split()
                            if len(parts) > 1:
                                module = parts[1].split('.')[0]  # Get top-level module
                                if module not in analysis.dependencies:
                                    analysis.dependencies.append(module)
            except (UnicodeDecodeError, PermissionError, FileNotFoundError):
                # Skip binary or inaccessible files
                pass
        
        # Build structure representation
        analysis.structure = self._build_structure_representation(files)
        
        return analysis
    
    def get_project_files(self, include_patterns: List[str] = None, 
                         exclude_patterns: List[str] = None) -> List[Path]:
        """Get list of project files matching patterns."""
        if include_patterns is None:
            include_patterns = ["**/*"]
        if exclude_patterns is None:
            exclude_patterns = [".git/**", "__pycache__/**", "node_modules/**"]
        
        files = []
        for pattern in include_patterns:
            matched_files = list(self.project_root.glob(pattern))
            for file_path in matched_files:
                if file_path.is_file():
                    # Check if file should be excluded
                    relative_path = file_path.relative_to(self.project_root)
                    should_exclude = False
                    for exclude_pattern in exclude_patterns:
                        if fnmatch.fnmatch(str(relative_path), exclude_pattern) or \
                           fnmatch.fnmatch(str(relative_path), exclude_pattern.rstrip('/')):
                            should_exclude = True
                            break
                    
                    if not should_exclude:
                        files.append(relative_path)
        
        return files
    
    def _build_structure_representation(self, files: List[Path]) -> Dict[str, Any]:
        """Build a hierarchical structure representation of the project."""
        structure = {}
        for file_path in files:
            parts = file_path.parts
            current = structure
            for part in parts[:-1]:  # All parts except the filename
                if part not in current:
                    current[part] = {}
                current = current[part]
            # Add the file
            current[parts[-1]] = None  # Files have no children
        return structure
    
    async def get_file_metadata(self, path: Path) -> FileMetadata:
        """Get metadata for a specific file."""
        full_path = self.project_root / path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        
        stat = full_path.stat()
        
        # Calculate content hash
        hash_md5 = hashlib.md5()
        try:
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            content_hash = hash_md5.hexdigest()
        except Exception:
            content_hash = ""
        
        # Count lines
        lines_count = 0
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines_count = len(f.readlines())
        except (UnicodeDecodeError, PermissionError):
            lines_count = 0
        
        # Determine file type by extension
        ext = path.suffix.lower()
        file_type = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.xml': 'XML',
            '.html': 'HTML',
            '.css': 'CSS'
        }.get(ext, 'Other')
        
        return FileMetadata(
            file_path=str(path),
            project_path=str(self.project_root),
            file_type=file_type,
            size_bytes=stat.st_size,
            lines_count=lines_count,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            content_hash=content_hash
        )
    
    async def search_files(self, search_term: str, file_patterns: List[str] = None) -> List[Path]:
        """Search for files containing a specific term."""
        if file_patterns is None:
            file_patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.java"]
        
        matching_files = []
        files = self.get_project_files(file_patterns)
        
        for file_path in files:
            try:
                full_path = self.project_root / file_path
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if search_term in content:
                        matching_files.append(file_path)
            except (UnicodeDecodeError, PermissionError, FileNotFoundError):
                # Skip files that can't be read
                pass
        
        return matching_files


class GitManager:
    """Git repository operations."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
    
    def get_recent_commits(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent git commits."""
        try:
            import subprocess
            import json
            from datetime import datetime, timedelta
            
            # Calculate the date for the specified number of days ago
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Run git log command to get recent commits
            result = subprocess.run([
                "git", "-C", str(self.repo_path), 
                "log", f"--since={since_date}", 
                "--pretty=format:{\"hash\":\"%H\",\"author\":\"%an\",\"email\":\"%ae\",\"date\":\"%ad\",\"message\":\"%s\"}",
                "--date=iso"
            ], capture_output=True, text=True, check=True)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        commit_data = json.loads(line)
                        commits.append(commit_data)
                    except json.JSONDecodeError:
                        # Skip lines that aren't valid JSON
                        continue
            
            return commits
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Return empty list if git command fails or git is not available
            return []
    
    def analyze_changes(self, since: str = "HEAD~10") -> Dict[str, Any]:
        """Analyze code changes in repository."""
        try:
            import subprocess
            
            # Get the diff stats
            result = subprocess.run([
                "git", "-C", str(self.repo_path),
                "diff", "--shortstat", since
            ], capture_output=True, text=True, check=True)
            
            # Get the list of changed files
            files_result = subprocess.run([
                "git", "-C", str(self.repo_path),
                "diff", "--name-only", since
            ], capture_output=True, text=True, check=True)
            
            # Get the diff summary by file type
            summary_result = subprocess.run([
                "git", "-C", str(self.repo_path),
                "diff", "--name-status", since
            ], capture_output=True, text=True, check=True)
            
            # Parse the results
            shortstat = result.stdout.strip()
            changed_files = files_result.stdout.strip().split('\n') if files_result.stdout.strip() else []
            
            # Count file types
            file_types = {}
            for file_path in changed_files:
                if file_path:
                    ext = Path(file_path).suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                "summary": shortstat,
                "changed_files": changed_files,
                "file_types": file_types,
                "total_files": len(changed_files)
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Return empty dict if git command fails or git is not available
            return {}
