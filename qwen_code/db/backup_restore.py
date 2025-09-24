"""
Backup and restore functionality for Qwen Code database.
"""

import os
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from qwen_code.utils.logging import get_logger
from qwen_code.db.encryption import EncryptionManager


logger = get_logger()


class BackupRestoreManager:
    """
    Manager for database backup and restore operations with encryption support.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.encryption_manager = EncryptionManager()
    
    def create_backup(self, backup_path: Path, encrypt: bool = True, 
                     include_sensitive: bool = True) -> bool:
        """
        Create a database backup with optional encryption.
        
        Args:
            backup_path: Path where the backup should be saved
            encrypt: Whether to encrypt the backup
            include_sensitive: Whether to include sensitive data in the backup
            
        Returns:
            True if backup was successful, False otherwise
        """
        try:
            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a timestamped backup name if needed
            if backup_path.suffix != '.zip':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_path.with_name(f"{backup_path.stem}_{timestamp}.zip")
            
            # Create backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add the database file
                zip_file.write(self.db_path, self.db_path.name)
                
                # Add schema information
                schema_info = {
                    "created_at": datetime.now().isoformat(),
                    "database_path": str(self.db_path),
                    "encrypted": encrypt,
                    "includes_sensitive": include_sensitive
                }
                
                zip_file.writestr("schema_info.json", json.dumps(schema_info, indent=2))
            
            # Encrypt the backup if requested
            if encrypt:
                self._encrypt_backup(backup_path)
            
            logger.info(f"Database backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return False
    
    def _encrypt_backup(self, backup_path: Path) -> None:
        """
        Encrypt the backup file.
        
        Args:
            backup_path: Path to the backup file to encrypt
        """
        # Read the backup file
        with open(backup_path, 'rb') as f:
            backup_data = f.read()
        
        # Encrypt the data
        encrypted_data = self.encryption_manager.encrypt_data(backup_data.decode('latin1'))
        
        # Write encrypted data back to file with .enc extension
        encrypted_path = backup_path.with_suffix(backup_path.suffix + '.enc')
        with open(encrypted_path, 'w') as f:
            f.write(encrypted_data)
        
        # Remove original unencrypted file
        os.remove(backup_path)
        
        logger.info(f"Backup encrypted: {encrypted_path}")
    
    def decrypt_backup(self, encrypted_backup_path: Path, output_path: Path) -> bool:
        """
        Decrypt a backup file.
        
        Args:
            encrypted_backup_path: Path to the encrypted backup file
            output_path: Path where the decrypted backup should be saved
            
        Returns:
            True if decryption was successful, False otherwise
        """
        try:
            # Read the encrypted backup
            with open(encrypted_backup_path, 'r') as f:
                encrypted_data = f.read()
            
            # Decrypt the data
            decrypted_data = self.encryption_manager.decrypt_data(encrypted_data)
            
            # Write decrypted data to output file
            with open(output_path, 'wb') as f:
                f.write(decrypted_data.encode('latin1'))
            
            logger.info(f"Backup decrypted: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to decrypt backup: {str(e)}")
            return False
    
    def restore_backup(self, backup_path: Path, restore_to: Optional[Path] = None, 
                      decrypt: bool = True) -> bool:
        """
        Restore database from a backup with optional decryption.
        
        Args:
            backup_path: Path to the backup file
            restore_to: Path where database should be restored (defaults to original location)
            decrypt: Whether to decrypt the backup before restoring
            
        Returns:
            True if restore was successful, False otherwise
        """
        try:
            restore_path = restore_to or self.db_path
            
            # Handle encrypted backups
            if backup_path.suffix == '.enc':
                if decrypt:
                    # Create temporary file for decrypted backup
                    temp_backup = backup_path.with_suffix('.zip')
                    if not self.decrypt_backup(backup_path, temp_backup):
                        return False
                    backup_path = temp_backup
                else:
                    logger.error("Cannot restore encrypted backup without decryption")
                    return False
            
            # Extract the backup
            with zipfile.ZipFile(backup_path, 'r') as zip_file:
                # Extract database file
                db_file_name = self.db_path.name
                if db_file_name in zip_file.namelist():
                    zip_file.extract(db_file_name, restore_path.parent)
                    
                    # Move the restored database to the correct location
                    extracted_db = restore_path.parent / db_file_name
                    shutil.move(str(extracted_db), str(restore_path))
                    
                    logger.info(f"Database restored to: {restore_path}")
                    
                    # Clean up temporary file if we created one
                    if backup_path.suffix == '.zip' and str(backup_path).endswith('_decrypted.zip'):
                        os.remove(backup_path)
                    
                    return True
                else:
                    logger.error(f"Database file {db_file_name} not found in backup")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            return False
    
    def get_backup_info(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get information about a backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Dictionary with backup information or None if failed
        """
        try:
            # Handle encrypted backups
            if backup_path.suffix == '.enc':
                # We can't read info from encrypted backups without decrypting
                # So we'll return basic info
                return {
                    "encrypted": True,
                    "size": backup_path.stat().st_size,
                    "modified": datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat()
                }
            
            with zipfile.ZipFile(backup_path, 'r') as zip_file:
                # Try to read schema info
                try:
                    schema_info_data = zip_file.read('schema_info.json')
                    schema_info = json.loads(schema_info_data.decode())
                    return schema_info
                except KeyError:
                    # If no schema_info.json, return basic info
                    return {
                        "encrypted": False,
                        "size": backup_path.stat().st_size,
                        "modified": datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat(),
                        "files": zip_file.namelist()
                    }
                    
        except Exception as e:
            logger.error(f"Failed to read backup info: {str(e)}")
            return None
    
    def list_backups(self, backup_directory: Path) -> List[Dict[str, Any]]:
        """
        List all backup files in a directory.
        
        Args:
            backup_directory: Directory to search for backups
            
        Returns:
            List of dictionaries with backup information
        """
        backups = []
        
        for file_path in backup_directory.glob("*.zip*"):  # Include both .zip and .zip.enc
            info = self.get_backup_info(file_path)
            if info:
                backups.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "info": info
                })
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x["info"].get("modified", ""), reverse=True)
        return backups
    
    def schedule_backups(self, backup_directory: Path, interval_hours: int = 24) -> None:
        """
        Schedule regular backups (placeholder for future implementation).
        
        Args:
            backup_directory: Directory where backups should be stored
            interval_hours: Interval between backups in hours
        """
        logger.info(f"Backup scheduling would be implemented here with interval: {interval_hours} hours")
        # This would typically integrate with a task scheduler system