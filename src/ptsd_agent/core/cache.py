"""Project-local caching system for PTSD Agent.

Provides hash-based caching for test discovery and counts to achieve
5-10x faster startup times. Cache is project-specific and invalidates
automatically when files change.

Cache Structure:
    <project_root>/.ptsd/cache/
    ├── test_counts.json     # Component test counts
    ├── file_hashes.json     # File modification tracking
    └── discovery_cache.json # Full discovery cache
"""

import json
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import time


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    data: Any
    timestamp: float
    file_hash: Optional[str] = None
    
    def is_valid(self, current_hash: Optional[str] = None, max_age_seconds: Optional[int] = None) -> bool:
        """Check if cache entry is still valid.
        
        Args:
            current_hash: Current file hash to compare against
            max_age_seconds: Maximum age in seconds (None = no age limit)
        
        Returns:
            True if cache is valid
        """
        # Check age if specified
        if max_age_seconds and (time.time() - self.timestamp) > max_age_seconds:
            return False
        
        # Check hash if provided
        if current_hash and self.file_hash and current_hash != self.file_hash:
            return False
        
        return True


class CacheManager:
    """Manages project-local caching for PTSD Agent."""
    
    def __init__(self, project_root: str):
        """Initialize cache manager.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.cache_dir = self.project_root / ".ptsd" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache files
        self.test_counts_file = self.cache_dir / "test_counts.json"
        self.file_hashes_file = self.cache_dir / "file_hashes.json"
        self.discovery_cache_file = self.cache_dir / "discovery_cache.json"
        
        # In-memory cache
        self._test_counts: Dict[str, CacheEntry] = {}
        self._file_hashes: Dict[str, str] = {}
        self._discovery_cache: Dict[str, CacheEntry] = {}
        
        # Load existing caches
        self._load_caches()
    
    def _load_caches(self):
        """Load existing caches from disk."""
        # Load test counts
        if self.test_counts_file.exists():
            try:
                with open(self.test_counts_file) as f:
                    data = json.load(f)
                    self._test_counts = {
                        k: CacheEntry(**v) for k, v in data.items()
                    }
            except Exception:
                pass
        
        # Load file hashes
        if self.file_hashes_file.exists():
            try:
                with open(self.file_hashes_file) as f:
                    self._file_hashes = json.load(f)
            except Exception:
                pass
        
        # Load discovery cache
        if self.discovery_cache_file.exists():
            try:
                with open(self.discovery_cache_file) as f:
                    data = json.load(f)
                    self._discovery_cache = {
                        k: CacheEntry(**v) for k, v in data.items()
                    }
            except Exception:
                pass
    
    def _save_caches(self):
        """Save caches to disk."""
        # Save test counts
        with open(self.test_counts_file, 'w') as f:
            data = {k: asdict(v) for k, v in self._test_counts.items()}
            json.dump(data, f, indent=2)
        
        # Save file hashes
        with open(self.file_hashes_file, 'w') as f:
            json.dump(self._file_hashes, f, indent=2)
        
        # Save discovery cache
        with open(self.discovery_cache_file, 'w') as f:
           data = {k: asdict(v) for k, v in self._discovery_cache.items()}
            json.dump(data, f, indent=2)
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file.
        
        Args:
            file_path: Path to file
        
        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
    
    def _compute_directory_hash(self, directory: str, patterns: List[str] = None) -> str:
        """Compute combined hash of directory contents.
        
        Args:
            directory: Directory path
            patterns: File patterns to include (e.g., ['*.py'])
        
        Returns:
            Combined hash of all matching files
        """
        hasher = hashlib.sha256()
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return ""
        
        # Collect all matching files
        files = []
        if patterns:
            for pattern in patterns:
                files.extend(dir_path.rglob(pattern))
        else:
            files = list(dir_path.rglob('*'))
        
        # Sort for consistency
        files = sorted([f for f in files if f.is_file()])
        
        # Hash each file
        for file_path in files:
            file_hash = self._compute_file_hash(str(file_path))
            hasher.update(file_hash.encode())
        
        return hasher.hexdigest()
    
    def get_test_count(self, component_name: str, directory: str) -> Optional[int]:
        """Get cached test count for component.
        
        Args:
            component_name: Component name
            directory: Component test directory
        
        Returns:
            Cached count if valid, None otherwise
        """
        # Check if we have cached count
        entry = self._test_counts.get(component_name)
        if not entry:
            return None
        
        # Compute current hash
        current_hash = self._compute_directory_hash(directory, ['test_*.py', '*_test.py'])
        
        # Check if cache is valid
        if entry.is_valid(current_hash):
            return entry.data
        
        return None
    
    def set_test_count(self, component_name: str, directory: str, count: int):
        """Cache test count for component.
        
        Args:
            component_name: Component name
            directory: Component test directory
            count: Test count
        """
        # Compute directory hash
        dir_hash = self._compute_directory_hash(directory, ['test_*.py', '*_test.py'])
        
        # Store entry
        self._test_counts[component_name] = CacheEntry(
            data=count,
            timestamp=time.time(),
            file_hash=dir_hash
        )
        
        # Save to disk
        self._save_caches()
    
    def get_discovery_result(self, component_name: str, directory: str) -> Optional[Dict]:
        """Get cached discovery result for component.
        
        Args:
            component_name: Component name
            directory: Component directory
        
        Returns:
            Cached discovery data if valid, None otherwise
        """
        entry = self._discovery_cache.get(component_name)
        if not entry:
            return None
        
        current_hash = self._compute_directory_hash(directory, ['*.py'])
        
        if entry.is_valid(current_hash):
            return entry.data
        
        return None
    
    def set_discovery_result(self, component_name: str, directory: str, result: Dict):
        """Cache discovery result for component.
        
        Args:
            component_name: Component name
            directory: Component directory
            result: Discovery result dictionary
        """
        dir_hash = self._compute_directory_hash(directory, ['*.py'])
        
        self._discovery_cache[component_name] = CacheEntry(
            data=result,
            timestamp=time.time(),
            file_hash=dir_hash
        )
        
        self._save_caches()
    
    def invalidate_component(self, component_name: str):
        """Invalidate all cache entries for a component.
        
        Args:
            component_name: Component to invalidate
        """
        self._test_counts.pop(component_name, None)
        self._discovery_cache.pop(component_name, None)
        self._save_caches()
    
    def clear_all(self):
        """Clear all caches."""
        self._test_counts.clear()
        self._file_hashes.clear()
        self._discovery_cache.clear()
        
        # Remove cache files
        for cache_file in [self.test_counts_file, self.file_hashes_file, self.discovery_cache_file]:
            if cache_file.exists():
                cache_file.unlink()
    
    def get_stats(self) -> Dict:
        """Get cache statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'test_counts_cached': len(self._test_counts),
            'discovery_results_cached': len(self._discovery_cache),
            'cache_dir': str(self.cache_dir),
            'total_size_bytes': sum(
                f.stat().st_size 
                for f in self.cache_dir.glob('*') 
                if f.is_file()
            )
        }
