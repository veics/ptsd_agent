"""Iteration state management for auto-install system.

Tracks iteration count and blockers across test runs to enable
smart auto-installation of external dependencies.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class IterationStateManager:
    """Manages iteration state and blocker tracking across runs."""
    
    STATE_FILE = ".ptsd/iteration_state.json"
    
    def __init__(self, base_dir: str = "."):
        """Initialize iteration state manager.
        
        Args:
            base_dir: Base directory for .ptsd folder
        """
        self.base_dir = Path(base_dir)
        self.state_path = self.base_dir / self.STATE_FILE
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load iteration state from file.
        
        Returns:
            State dictionary with iteration info and blockers
        """
        if not self.state_path.exists():
            return self._create_default_state()
        
        try:
            with open(self.state_path) as f:
                state = json.load(f)
            logger.debug(f"Loaded iteration state: iteration {state.get('iteration', 0)}")
            return state
        except Exception as e:
            logger.warning(f"Failed to load iteration state: {e}")
            return self._create_default_state()
    
    def _create_default_state(self) -> Dict[str, Any]:
        """Create default state structure.
        
        Returns:
            Default state dictionary
        """
        return {
            "iteration": 0,
            "last_run": None,
            "run_id": None,
            "blockers": {
                "external": [],
                "internal": []
            },
            "auto_install_enabled": False
        }
    
    def save_state(self, blockers: Dict[str, List], run_id: str = None):
        """Save current state to file.
        
        Args:
            blockers: Dictionary with 'external' and 'internal' blocker lists
            run_id: Optional run ID for this execution
        """
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        self.state["run_id"] = run_id or self.state.get("run_id")
        self.state["blockers"] = blockers
        
        try:
            # Ensure directory exists
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_path, 'w') as f:
                json.dump(self.state, f, indent=2)
            
            logger.debug(f"Saved iteration state: {len(blockers.get('external', []))} external blockers")
        except Exception as e:
            logger.error(f"Failed to save iteration state: {e}")
    
    def increment_iteration(self):
        """Increment iteration counter."""
        self.state["iteration"] += 1
        logger.info(f"Incremented iteration to {self.state['iteration']}")
    
    def reset(self):
        """Reset iteration state to defaults."""
        self.state = self._create_default_state()
        if self.state_path.exists():
            self.state_path.unlink()
        logger.info("Reset iteration state")
    
    def should_auto_install(self, config: Dict[str, Any]) -> bool:
        """Check if auto-install should trigger.
        
        Args:
            config: Configuration dictionary with auto_install settings
        
        Returns:
            True if auto-install should run
        """
        auto_install_config = config.get('dependency_updates', {}).get('auto_install', {})
        
        if not auto_install_config.get('enabled', False):
            return False
        
        # Check iteration threshold
        on_iteration = auto_install_config.get('on_iteration', 2)
        if self.state["iteration"] < on_iteration:
            logger.debug(f"Auto-install skipped: iteration {self.state['iteration']} < {on_iteration}")
            return False
        
        # Check for external blockers
        external_blockers = self.state.get("blockers", {}).get("external", [])
        if not external_blockers:
            logger.debug("Auto-install skipped: no external blockers")
            return False
        
        logger.info(f"Auto-install should run: iteration {self.state['iteration']}, {len(external_blockers)} blockers")
        return True
    
    def get_external_blockers(self) -> List[Dict[str, Any]]:
        """Get list of external blockers from state.
        
        Returns:
            List of external blocker dictionaries
        """
        return self.state.get("blockers", {}).get("external", [])
    
    def get_iteration(self) -> int:
        """Get current iteration number.
        
        Returns:
            Current iteration count
        """
        return self.state.get("iteration", 0)
    
    def has_pending_blockers(self) -> bool:
        """Check if there are pending blockers.
        
        Returns:
            True if blockers exist
        """
        blockers = self.state.get("blockers", {})
        return bool(blockers.get("external") or blockers.get("internal"))
