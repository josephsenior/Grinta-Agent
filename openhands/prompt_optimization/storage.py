"""
Storage Backend for Dynamic Prompt Optimization.

Implements hybrid storage with local cache and optional central sync
for prompt variants and performance data.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .registry import PromptRegistry
from .tracker import PerformanceTracker
from .models import OptimizationConfig


class PromptStorage:
    """Hybrid storage backend for prompt optimization data."""
    
    def __init__(self, config: OptimizationConfig, registry: PromptRegistry, 
                 tracker: PerformanceTracker):
        """Initialize the storage backend.
        
        Args:
            config: Optimization configuration
            registry: Prompt registry to persist
            tracker: Performance tracker to persist
        """
        self.config = config
        self.registry = registry
        self.tracker = tracker
        
        # Storage paths
        self.storage_path = Path(config.storage_path).expanduser()
        self.registry_file = self.storage_path / "registry.json"
        self.tracker_file = self.storage_path / "tracker.json"
        self.config_file = self.storage_path / "config.json"
        self.metadata_file = self.storage_path / "metadata.json"
        
        # Thread safety
        self._lock = threading.RLock()
        self._update_count = 0
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        self.load_all()
    
    def save_all(self) -> bool:
        """Save all data to storage."""
        with self._lock:
            try:
                # Save registry data
                registry_data = self.registry.export_data()
                with open(self.registry_file, 'w') as f:
                    json.dump(registry_data, f, indent=2)
                
                # Save tracker data
                tracker_data = self.tracker.export_data()
                with open(self.tracker_file, 'w') as f:
                    json.dump(tracker_data, f, indent=2)
                
                # Save config
                with open(self.config_file, 'w') as f:
                    json.dump(self.config.to_dict(), f, indent=2)
                
                # Save metadata
                metadata = {
                    'last_saved': datetime.now().isoformat(),
                    'update_count': self._update_count,
                    'version': '1.0'
                }
                with open(self.metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return True
                
            except Exception as e:
                print(f"Error saving prompt optimization data: {e}")
                return False
    
    def load_all(self) -> bool:
        """Load all data from storage."""
        with self._lock:
            try:
                # Load registry data
                if self.registry_file.exists():
                    with open(self.registry_file, 'r') as f:
                        registry_data = json.load(f)
                    self.registry.import_data(registry_data)
                
                # Load tracker data
                if self.tracker_file.exists():
                    with open(self.tracker_file, 'r') as f:
                        tracker_data = json.load(f)
                    self.tracker.import_data(tracker_data)
                
                # Load config (merge with current config)
                if self.config_file.exists():
                    with open(self.config_file, 'r') as f:
                        saved_config = json.load(f)
                    # Update current config with saved values
                    for key, value in saved_config.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
                
                # Load metadata
                if self.metadata_file.exists():
                    with open(self.metadata_file, 'r') as f:
                        metadata = json.load(f)
                    self._update_count = metadata.get('update_count', 0)
                
                return True
                
            except Exception as e:
                print(f"Error loading prompt optimization data: {e}")
                return False
    
    def auto_save(self) -> bool:
        """Auto-save if enabled and sync interval reached."""
        if not self.config.auto_save:
            return True
        
        with self._lock:
            self._update_count += 1
            
            # Check if we should save
            if self._update_count % self.config.sync_interval == 0:
                return self.save_all()
            
            return True
    
    def force_save(self) -> bool:
        """Force save regardless of sync interval."""
        return self.save_all()
    
    def backup_data(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of all data."""
        if backup_path is None:
            backup_path = self.storage_path / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = Path(backup_path)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy all files to backup location
            import shutil
            
            for file_path in [self.registry_file, self.tracker_file, 
                            self.config_file, self.metadata_file]:
                if file_path.exists():
                    shutil.copy2(file_path, backup_path / file_path.name)
            
            return True
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore data from a backup."""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            print(f"Backup path does not exist: {backup_path}")
            return False
        
        try:
            # Create temporary backup of current data
            current_backup = self.storage_path / f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.backup_data(current_backup)
            
            # Restore from backup
            import shutil
            
            for file_name in ["registry.json", "tracker.json", "config.json", "metadata.json"]:
                backup_file = backup_path / file_name
                if backup_file.exists():
                    shutil.copy2(backup_file, self.storage_path / file_name)
            
            # Reload data
            return self.load_all()
            
        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about storage state."""
        with self._lock:
            info = {
                'storage_path': str(self.storage_path),
                'files_exist': {
                    'registry': self.registry_file.exists(),
                    'tracker': self.tracker_file.exists(),
                    'config': self.config_file.exists(),
                    'metadata': self.metadata_file.exists()
                },
                'update_count': self._update_count,
                'last_saved': None,
                'file_sizes': {}
            }
            
            # Get file sizes
            for file_name, file_path in [
                ('registry', self.registry_file),
                ('tracker', self.tracker_file),
                ('config', self.config_file),
                ('metadata', self.metadata_file)
            ]:
                if file_path.exists():
                    info['file_sizes'][file_name] = file_path.stat().st_size
            
            # Get last saved time from metadata
            if self.metadata_file.exists():
                try:
                    with open(self.metadata_file, 'r') as f:
                        metadata = json.load(f)
                    info['last_saved'] = metadata.get('last_saved')
                except:
                    pass
            
            return info
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old performance data to save space."""
        try:
            # This would be implemented based on specific requirements
            # For now, we'll just clean up old performance data
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Get all performance data
            all_performances = []
            for variant_id in self.registry._variants.keys():
                variant_performances = [
                    p for p in self.tracker._performance_data
                    if p.variant_id == variant_id
                ]
                all_performances.extend(variant_performances)
            
            # Filter out old data
            recent_performances = [
                p for p in all_performances
                if p.timestamp >= cutoff_date
            ]
            
            # Update tracker with only recent data
            self.tracker._performance_data = recent_performances
            
            # Recalculate metrics
            for variant_id in self.registry._variants.keys():
                self.tracker._update_variant_metrics_from_performances(variant_id)
            
            return True
            
        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            return False
    
    def export_data(self, export_path: str) -> bool:
        """Export all data to a specific location."""
        export_path = Path(export_path)
        export_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Export registry data
            registry_data = self.registry.export_data()
            with open(export_path / "registry.json", 'w') as f:
                json.dump(registry_data, f, indent=2)
            
            # Export tracker data
            tracker_data = self.tracker.export_data()
            with open(export_path / "tracker.json", 'w') as f:
                json.dump(tracker_data, f, indent=2)
            
            # Export config
            with open(export_path / "config.json", 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            
            # Export metadata
            metadata = {
                'exported_at': datetime.now().isoformat(),
                'update_count': self._update_count,
                'version': '1.0'
            }
            with open(export_path / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False
    
    def import_data(self, import_path: str) -> bool:
        """Import data from a specific location."""
        import_path = Path(import_path)
        
        if not import_path.exists():
            print(f"Import path does not exist: {import_path}")
            return False
        
        try:
            # Create backup before import
            self.backup_data()
            
            # Import registry data
            registry_file = import_path / "registry.json"
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    registry_data = json.load(f)
                self.registry.import_data(registry_data)
            
            # Import tracker data
            tracker_file = import_path / "tracker.json"
            if tracker_file.exists():
                with open(tracker_file, 'r') as f:
                    tracker_data = json.load(f)
                self.tracker.import_data(tracker_data)
            
            # Import config
            config_file = import_path / "config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                # Update current config
                for key, value in config_data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            
            return True
            
        except Exception as e:
            print(f"Error importing data: {e}")
            return False
    
    def clear_all_data(self) -> bool:
        """Clear all stored data."""
        with self._lock:
            try:
                # Clear in-memory data
                self.registry.clear()
                self.tracker.clear_data()
                
                # Remove files
                for file_path in [self.registry_file, self.tracker_file, 
                                self.config_file, self.metadata_file]:
                    if file_path.exists():
                        file_path.unlink()
                
                # Reset update count
                self._update_count = 0
                
                return True
                
            except Exception as e:
                print(f"Error clearing data: {e}")
                return False
    
    def get_data_size(self) -> Dict[str, int]:
        """Get the size of stored data."""
        sizes = {}
        
        for file_name, file_path in [
            ('registry', self.registry_file),
            ('tracker', self.tracker_file),
            ('config', self.config_file),
            ('metadata', self.metadata_file)
        ]:
            if file_path.exists():
                sizes[file_name] = file_path.stat().st_size
            else:
                sizes[file_name] = 0
        
        sizes['total'] = sum(sizes.values())
        return sizes
