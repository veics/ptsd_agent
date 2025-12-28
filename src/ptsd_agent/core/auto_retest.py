"""Auto-retest coordinator for dependency-blocked components.

Automatically retests components when their blockers are fixed.
"""

from typing import Dict, List, Set, Optional
from datetime import datetime, timezone
import json


class AutoRetestCoordinator:
    """Coordinates automatic retesting when blockers clear."""
    
    def __init__(self, history_store):
        """Initialize coordinator.
        
        Args:
            history_store: HistoryStore instance for persistence
        """
        self.history = history_store
        self.blocked_components: Dict[str, Set[str]] = {}
        self.blocker_status: Dict[str, bool] = {}
    
    def record_blocked(self, component: str, blockers: List[str]):
        """Record that a component is blocked.
        
        Args:
            component: Component that is blocked
            blockers: List of components blocking it
        """
        if component not in self.blocked_components:
            self.blocked_components[component] = set()
        
        self.blocked_components[component].update(blockers)
        
        # Record in database for persistence
        self._save_blocker_state(component, list(self.blocked_components[component]))
    
    def update_blocker_status(self, component: str, passed: bool):
        """Update status of a potential blocker component.
        
        Args:
            component: Component name
            passed: True if tests passed, False if failed
        """
        self.blocker_status[component] = passed
    
    def get_components_to_retest(self) -> List[str]:
        """Get components that should be retested because blockers cleared.
        
        Returns:
            List of component names to retest
        """
        to_retest = []
        
        for component, blockers in self.blocked_components.items():
            # Check if all blockers have now passed
            all_clear = all(
                self.blocker_status.get(blocker, False)
                for blocker in blockers
            )
            
            if all_clear:
                to_retest.append(component)
        
        return to_retest
    
    def clear_blocked(self, component: str):
        """Clear blocked status for a component.
        
        Args:
            component: Component to clear
        """
        if component in self.blocked_components:
            del self.blocked_components[component]
            self._delete_blocker_state(component)
    
    def load_previous_blockers(self, run_id: str = None):
        """Load blocker state from previous run.
        
        Args:
            run_id: Optional specific run ID, otherwise uses latest
        """
        # TODO: Query from database
        # For now, start fresh each session
        pass
    
    def _save_blocker_state(self, component: str, blockers: List[str]):
        """Save blocker state to database."""
        # Use database to persist blocker relationships
        # This allows auto-retest across runs
        conn = self.history._get_connection() if hasattr(self.history, '_get_connection') else None
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocker_state (
                    component TEXT PRIMARY KEY,
                    blockers TEXT,
                    recorded_at TEXT
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO blocker_state (component, blockers, recorded_at)
                VALUES (?, ?, ?)
            """, (component, json.dumps(blockers), datetime.now(timezone.utc).isoformat()))
            
            conn.commit()
        except Exception:
            pass  # Gracefully handle if database unavailable
    
    def _delete_blocker_state(self, component: str):
        """Delete blocker state from database."""
        conn = self.history._get_connection() if hasattr(self.history, '_get_connection') else None
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blocker_state WHERE component = ?", (component,))
            conn.commit()
        except Exception:
            pass


def should_auto_retest(coordinator: AutoRetestCoordinator, component: str) -> bool:
    """Check if component should be auto-retested.
    
    Args:
        coordinator: AutoRetestCoordinator instance
        component: Component name
    
    Returns:
        True if should retest
    """
    return component in coordinator.get_components_to_retest()
