"""
Unit tests for Qwen Code file system operations.
"""

import pytest
import tempfile
import os
from pathlib import Path
from qwen_code.fs.operations import FileManager, CodebaseAnalysis, FileMetadata


class TestFileManager:
    """Test file manager operations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project structure for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create some test files
            (project_path / "main.py").write_text("print('Hello, World!')\n")
            (project_path / "utils.py").write_text("def helper():\n    return 'utils'\n")
            (project_path / "README.md").write_text("# Test Project\n")
            (project_path / ".git").mkdir()
            (project_path / ".git" / "config").write_text("[core]\n")
            (project_path / "node_modules").mkdir()
            (project_path / "node_modules" / "package.json").write_text("{}")
            
            yield project_path
    
    def test_init(self, temp_project):
        """Test file manager initialization."""
        fm = FileManager(temp_project)
        assert fm.project_root == temp_project
    
    @pytest.mark.asyncio
    async def test_read_file(self, temp_project):
        """Test reading a file."""
        fm = FileManager(temp_project)
        content = await fm.read_file(Path("main.py"))
        assert content == "print('Hello, World!')\n"
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_project):
        """Test reading a nonexistent file."""
        fm = FileManager(temp_project)
        with pytest.raises(FileNotFoundError):
            await fm.read_file(Path("nonexistent.py"))
    
    @pytest.mark.asyncio
    async def test_write_file(self, temp_project):
        """Test writing a file."""
        fm = FileManager(temp_project)
        await fm.write_file(Path("new_file.py"), "print('New file')")
        
        # Verify the file was created
        content = await fm.read_file(Path("new_file.py"))
        assert content == "print('New file')"
    
    @pytest.mark.asyncio
    async def test_write_file_creates_backup(self, temp_project):
        """Test that writing a file creates a backup if it already exists."""
        fm = FileManager(temp_project)
        
        # Write initial content
        await fm.write_file(Path("test.py"), "print('Original')")
        
        # Write new content (should create backup)
        await fm.write_file(Path("test.py"), "print('Updated')")
        
        # Verify the file was updated
        content = await fm.read_file(Path("test.py"))
        assert content == "print('Updated')"
        
        # Verify backup was created
        backup_path = temp_project / "test.py.backup"
        assert backup_path.exists()
        assert backup_path.read_text() == "print('Original')"
    
    def test_get_project_files(self, temp_project):
        """Test getting project files with patterns."""
        fm = FileManager(temp_project)
        
        # Get all Python files
        files = fm.get_project_files(["**/*.py"])
        assert len(files) == 2
        assert Path("main.py") in files
        assert Path("utils.py") in files
        
        # Get all files (should exclude .git and node_modules by default)
        files = fm.get_project_files(["**/*"])
        # Should include main.py, utils.py, README.md
        assert len(files) >= 3
        assert Path("main.py") in files
        assert Path("utils.py") in files
        assert Path("README.md") in files
        # Should not include .git or node_modules files
        assert not any(".git" in str(f) for f in files)
        assert not any("node_modules" in str(f) for f in files)
    
    @pytest.mark.asyncio
    async def test_analyze_codebase(self, temp_project):
        """Test codebase analysis."""
        fm = FileManager(temp_project)
        analysis = await fm.analyze_codebase()
        
        assert isinstance(analysis, CodebaseAnalysis)
        assert analysis.total_files >= 2  # main.py and utils.py
        assert analysis.total_lines >= 2  # At least 2 lines
        assert "Python" in analysis.languages
        assert analysis.languages["Python"] >= 2
        
        # Check structure representation
        structure_str = str(analysis.structure)
        assert "main.py" in structure_str
        assert "utils.py" in structure_str
    
    @pytest.mark.asyncio
    async def test_get_file_metadata(self, temp_project):
        """Test getting file metadata."""
        fm = FileManager(temp_project)
        metadata = await fm.get_file_metadata(Path("main.py"))
        
        assert isinstance(metadata, FileMetadata)
        assert metadata.file_path == "main.py"
        assert metadata.file_type == "Python"
        assert metadata.size_bytes > 0
        assert metadata.lines_count > 0
        assert metadata.content_hash != ""
        assert metadata.last_modified is not None
    
    @pytest.mark.asyncio
    async def test_search_files(self, temp_project):
        """Test searching files for content."""
        fm = FileManager(temp_project)
        matching_files = await fm.search_files("Hello")
        
        assert len(matching_files) == 1
        assert Path("main.py") in matching_files


class TestCodebaseAnalysis:
    """Test codebase analysis data class."""
    
    def test_initialization(self):
        """Test codebase analysis initialization."""
        analysis = CodebaseAnalysis()
        assert analysis.total_files == 0
        assert analysis.total_lines == 0
        assert analysis.languages == {}
        assert analysis.dependencies == []
        assert analysis.structure == {}


class TestFileMetadata:
    """Test file metadata data class."""
    
    def test_initialization(self):
        """Test file metadata initialization."""
        metadata = FileMetadata(
            file_path="test.py",
            project_path="/test/project",
            file_type="Python",
            size_bytes=100,
            lines_count=5,
            last_modified="2023-01-01T00:00:00",
            content_hash="abc123"
        )
        assert metadata.file_path == "test.py"
        assert metadata.project_path == "/test/project"
        assert metadata.file_type == "Python"
        assert metadata.size_bytes == 100
        assert metadata.lines_count == 5
        assert metadata.last_modified == "2023-01-01T00:00:00"
        assert metadata.content_hash == "abc123"
        assert metadata.analysis_data == {}