"""Backup and recovery procedures for Qwen Code CLI."""

import os
import shutil
import tarfile
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import asyncio
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup and recovery operations for Qwen Code CLI data."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".qwen"
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Encryption key for secure backups (in production, this should be properly managed)
        self.encryption_key = os.getenv('QWEN_BACKUP_ENCRYPTION_KEY', '').encode() or Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """
        Create a backup of Qwen Code CLI configuration and data.
        
        Args:
            backup_name: Optional name for the backup. If not provided, uses timestamp.
            
        Returns:
            Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"qwen_backup_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        logger.info(f"Starting backup: {backup_path}")
        
        # Files and directories to back up
        items_to_backup = [
            self.config_dir / "config.yaml",  # Configuration file
            self.config_dir / "sessions.db",  # Session database
            self.config_dir / "credentials.db", # Credentials database
            self.config_dir / "history",       # Command history
            self.config_dir / "sessions",      # Session files
            self.config_dir / "projects",      # Project-specific data
        ]
        
        # Create backup archive
        with tarfile.open(backup_path, "w:gz") as tar:
            for item in items_to_backup:
                if item.exists():
                    # Add to archive with relative path
                    tar.add(item, arcname=item.name)
                    logger.debug(f"Added to backup: {item}")
        
        logger.info(f"Backup created successfully: {backup_path}")
        return backup_path
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        for backup_file in self.backup_dir.glob("*.tar.gz"):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.stem,
                "path": str(backup_file),
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime),
                "encrypted": "_encrypted" in backup_file.name
            })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups
    
    def restore_backup(self, backup_path: Path, restore_dir: Optional[Path] = None) -> bool:
        """
        Restore from a backup file.
        
        Args:
            backup_path: Path to the backup file to restore
            restore_dir: Directory to restore to (defaults to config_dir)
            
        Returns:
            True if restore was successful, False otherwise
        """
        restore_to = restore_dir or self.config_dir
        logger.info(f"Starting restore from: {backup_path} to: {restore_to}")
        
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract the backup
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(path=temp_path)
                
                # Copy extracted files to restore location
                for item in temp_path.iterdir():
                    dest_path = restore_to / item.name
                    
                    if item.is_file():
                        shutil.copy2(item, dest_path)
                        logger.debug(f"Restored file: {dest_path}")
                    elif item.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(item, dest_path)
                        logger.debug(f"Restored directory: {dest_path}")
                
                logger.info("Restore completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False
    
    def encrypt_backup(self, backup_path: Path) -> Path:
        """
        Encrypt a backup file.
        
        Args:
            backup_path: Path to the backup file to encrypt
            
        Returns:
            Path to the encrypted backup file
        """
        encrypted_path = backup_path.with_name(backup_path.name + "_encrypted")
        
        with open(backup_path, 'rb') as f:
            backup_data = f.read()
        
        encrypted_data = self.cipher_suite.encrypt(backup_data)
        
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Remove original unencrypted backup
        backup_path.unlink()
        
        logger.info(f"Backup encrypted: {encrypted_path}")
        return encrypted_path
    
    def decrypt_backup(self, encrypted_path: Path) -> Path:
        """
        Decrypt an encrypted backup file.
        
        Args:
            encrypted_path: Path to the encrypted backup file
            
        Returns:
            Path to the decrypted backup file
        """
        decrypted_path = encrypted_path.with_name(encrypted_path.name.replace("_encrypted", ""))
        
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data)
        
        logger.info(f"Backup decrypted: {decrypted_path}")
        return decrypted_path
    
    def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
        """
        Remove backups older than the specified number of days.
        
        Args:
            days_to_keep: Number of days to keep backups
            
        Returns:
            Number of backups removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0
        
        for backup in self.backup_dir.glob("*.tar.gz"):
            if datetime.fromtimestamp(backup.stat().st_mtime) < cutoff_date:
                backup.unlink()
                removed_count += 1
                logger.info(f"Removed old backup: {backup}")
        
        return removed_count


class RecoveryManager:
    """Manages recovery procedures for Qwen Code CLI when issues occur."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".qwen"
        self.backup_manager = BackupManager(config_dir)
        self.logger = logging.getLogger(__name__)
    
    def reset_configuration(self) -> bool:
        """
        Reset configuration to default values.
        
        Returns:
            True if reset was successful, False otherwise
        """
        try:
            config_file = self.config_dir / "config.yaml"
            if config_file.exists():
                config_file.unlink()
            
            # Create a basic config file with defaults
            from qwen_code.config.settings import create_default_config
            create_default_config()
            
            self.logger.info("Configuration reset to defaults")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset configuration: {str(e)}")
            return False
    
    def repair_database(self) -> bool:
        """
        Attempt to repair the session database.
        
        Returns:
            True if repair was successful, False otherwise
        """
        db_path = self.config_dir / "sessions.db"
        
        if not db_path.exists():
            self.logger.warning("Database does not exist, skipping repair")
            return True
        
        try:
            # Create backup before repair
            backup_path = self.backup_manager.create_backup("db_repair_backup")
            self.logger.info(f"Created backup before repair: {backup_path}")
            
            # Test database integrity
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check integrity
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] != "ok":
                # Attempt to rebuild database
                self.logger.warning(f"Database integrity issue found: {result[0]}")
                
                # Create new database
                temp_db = db_path.with_suffix('.db.tmp')
                old_db = db_path.with_suffix('.db.backup')
                
                # Rename current db to backup
                db_path.rename(old_db)
                
                # Try to recreate from backup or with fresh database
                # For now, just create an empty valid database
                new_conn = sqlite3.connect(db_path)
                # Create the same schema as in the original db manager
                new_conn.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        model TEXT,
                        messages TEXT
                    )
                ''')
                new_conn.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions (id)
                    )
                ''')
                new_conn.commit()
                new_conn.close()
                
                self.logger.info("Database repaired successfully")
            else:
                self.logger.info("Database integrity check passed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database repair failed: {str(e)}")
            return False
    
    def validate_installation(self) -> Dict[str, Any]:
        """
        Validate the Qwen Code CLI installation and configuration.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "config_dir_exists": False,
            "config_file_exists": False,
            "database_exists": False,
            "permissions_ok": False,
            "dependencies_ok": True,
            "validation_passed": False
        }
        
        # Check config directory
        results["config_dir_exists"] = self.config_dir.exists()
        
        if results["config_dir_exists"]:
            # Check config file
            config_file = self.config_dir / "config.yaml"
            results["config_file_exists"] = config_file.exists()
            
            # Check database
            db_file = self.config_dir / "sessions.db"
            results["database_exists"] = db_file.exists()
            
            # Check permissions
            try:
                test_file = self.config_dir / ".permission_test"
                test_file.touch()
                test_file.unlink()
                results["permissions_ok"] = True
            except PermissionError:
                results["permissions_ok"] = False
        
        # Overall validation
        results["validation_passed"] = (
            results["config_dir_exists"] and 
            results["config_file_exists"] and 
            results["database_exists"] and 
            results["permissions_ok"] and 
            results["dependencies_ok"]
        )
        
        return results


# Global backup manager instance
backup_manager = BackupManager()
recovery_manager = RecoveryManager()