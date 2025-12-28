"""
PTSD Agent History Storage

Dual storage backend for test run history:
- JSON files in .ptsd/history/ for human readability and git-friendly storage
- SQLite database in .ptsd/metrics.db for fast queries

Stores ALL data including:
- Run metadata (timestamp, duration, git info)
- Phase/component metrics (coverage, warnings, failures, errors, skipped, pass_rate)
- Test file details and counts
- Last iteration of test logs for bugfixing
"""

import json
import sqlite3
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import shutil


class HistoryStore:
    """Dual storage backend for test run history."""
    
    def __init__(self, base_dir: str = ".ptsd"):
        self.base_dir = Path(base_dir)
        self.history_dir = self.base_dir / "history"
        self.logs_dir = self.base_dir / "logs"
        self.db_path = self.base_dir / "metrics.db"
        
        # Ensure directories exist
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Runs table - main run metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                duration_seconds REAL,
                git_branch TEXT,
                git_commit TEXT,
                git_dirty INTEGER,
                total_phases INTEGER,
                total_components INTEGER,
                total_tests INTEGER,
                overall_coverage REAL,
                overall_pass_rate REAL,
                overall_failures INTEGER,
                overall_errors INTEGER,
                overall_warnings INTEGER,
                overall_skipped INTEGER,
                config_hash TEXT,
                json_path TEXT
            )
        """)
        
        # Phase metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phase_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                phase_id INTEGER NOT NULL,
                phase_name TEXT,
                coverage REAL,
                warnings INTEGER,
                failures INTEGER,
                errors INTEGER,
                skipped INTEGER,
                total_tests INTEGER,
                pass_rate REAL,
                duration_seconds REAL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Component metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS component_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                phase_id INTEGER NOT NULL,
                component_name TEXT NOT NULL,
                coverage REAL,
                warnings INTEGER,
                failures INTEGER,
                errors INTEGER,
                skipped INTEGER,
                total_tests INTEGER,
                pass_rate REAL,
                duration_seconds REAL,
                test_path TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Test file details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                component_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                test_count INTEGER,
                passed INTEGER,
                failed INTEGER,
                errors INTEGER,
                skipped INTEGER,
                duration_seconds REAL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Skip events for audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skip_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                test_name TEXT NOT NULL,
                component TEXT NOT NULL,
                reason TEXT NOT NULL,
                marker TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                phase_id INTEGER,
                file_path TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_phase_run ON phase_metrics(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_component_run ON component_metrics(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_run ON test_files(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skip_test ON skip_events(test_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skip_component ON skip_events(component)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skip_run ON skip_events(run_id)")
        
        conn.commit()
        conn.close()
    
    def _get_git_info(self) -> Dict[str, Any]:
        """Get current git repository information."""
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()[:12]
            
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip() != ""
            
            return {"branch": branch, "commit": commit, "dirty": dirty}
        except Exception:
            return {"branch": None, "commit": None, "dirty": None}
    
    def save_run(self, state: Dict, file_details: Dict = None, logs: Dict = None) -> str:
        """
        Save test run to both JSON and SQLite.
        
        Args:
            state: The full test state dict from main.py
            file_details: Optional per-file test details
            logs: Optional test logs (last iteration only)
        
        Returns:
            run_id: Unique identifier for this run
        """
        run_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(timezone.utc).isoformat()
        git_info = self._get_git_info()
        
        # Build comprehensive run data
        run_data = {
            "run_id": run_id,
            "timestamp": timestamp,
            "duration_seconds": state.get("duration_seconds", 0),
            "git": git_info,
            "config": {
                "phases_requested": state.get("phases_requested", []),
                "parallel": state.get("parallel", False),
                "collapsed": state.get("collapsed", []),
            },
            "overall": {
                "coverage": state.get("overall_coverage", 0),
                "warnings": state.get("overall_warnings", 0),
                "failures": state.get("overall_failures", 0),
                "errors": state.get("overall_errors", 0),
                "skipped": state.get("overall_skipped", 0),
                "total_tests": state.get("overall_tests", 0),
                "pass_rate": state.get("overall_pass_rate", 0),
                "progress": state.get("overall_progress", 0),
            },
            "phases": {},
            "file_details": file_details or {},
        }
        
        # Process phases
        phases = state.get("phases", {})
        for phase_id, phase_data in phases.items():
            phase_entry = {
                "name": phase_data.get("name", f"Phase {phase_id}"),
                "status": phase_data.get("status", ""),
                "metrics": {
                    "coverage": phase_data.get("coverage", 0),
                    "warnings": phase_data.get("warnings", 0),
                    "failures": phase_data.get("failures", 0),
                    "errors": phase_data.get("errors", 0),
                    "skipped": phase_data.get("skipped", 0),
                    "total_tests": phase_data.get("total_tests", 0),
                    "pass_rate": phase_data.get("pass_rate", 0),
                },
                "components": {}
            }
            
            # Process components
            components = phase_data.get("components", {})
            for comp_name, comp_data in components.items():
                phase_entry["components"][comp_name] = {
                    "coverage": comp_data.get("coverage", 0),
                    "warnings": comp_data.get("warnings", 0),
                    "failures": comp_data.get("failures", 0),
                    "errors": comp_data.get("errors", 0),
                    "skipped": comp_data.get("skipped", 0),
                    "total_tests": comp_data.get("total_tests", 0),
                    "pass_rate": comp_data.get("pass_rate", 0),
                    "progress": comp_data.get("progress", 0),
                    "status": comp_data.get("status", ""),
                    "test_path": comp_data.get("test_path", ""),
                }
            
            run_data["phases"][str(phase_id)] = phase_entry
        
        # Save JSON file
        json_filename = f"{timestamp.replace(':', '-').replace('+', '_')}_{run_id}.json"
        json_path = self.history_dir / json_filename
        with open(json_path, 'w') as f:
            json.dump(run_data, f, indent=2)
        
        # Save logs (last iteration only, for bugfixing)
        if logs:
            logs_path = self.logs_dir / f"latest_{run_id}.json"
            with open(logs_path, 'w') as f:
                json.dump(logs, f, indent=2)
            
            # Clean up old log files, keep only the latest
            for old_log in self.logs_dir.glob("latest_*.json"):
                if old_log.name != f"latest_{run_id}.json":
                    old_log.unlink()
        
        # Save to SQLite
        self._save_to_db(run_data, str(json_path))
        
        return run_id
    
    def _save_to_db(self, run_data: Dict, json_path: str):
        """Save run data to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        git = run_data.get("git", {})
        overall = run_data.get("overall", {})
        phases = run_data.get("phases", {})
        
        # Insert main run record
        cursor.execute("""
            INSERT INTO runs (
                run_id, timestamp, duration_seconds,
                git_branch, git_commit, git_dirty,
                total_phases, total_components, total_tests,
                overall_coverage, overall_pass_rate,
                overall_failures, overall_errors, overall_warnings, overall_skipped,
                json_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_data["run_id"],
            run_data["timestamp"],
            run_data.get("duration_seconds", 0),
            git.get("branch"),
            git.get("commit"),
            1 if git.get("dirty") else 0,
            len(phases),
            sum(len(p.get("components", {})) for p in phases.values()),
            overall.get("total_tests", 0),
            overall.get("coverage", 0),
            overall.get("pass_rate", 0),
            overall.get("failures", 0),
            overall.get("errors", 0),
            overall.get("warnings", 0),
            overall.get("skipped", 0),
            json_path
        ))
        
        # Insert phase metrics
        for phase_id, phase_data in phases.items():
            metrics = phase_data.get("metrics", {})
            cursor.execute("""
                INSERT INTO phase_metrics (
                    run_id, phase_id, phase_name,
                    coverage, warnings, failures, errors, skipped,
                    total_tests, pass_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_data["run_id"],
                int(phase_id),
                phase_data.get("name", ""),
                metrics.get("coverage", 0),
                metrics.get("warnings", 0),
                metrics.get("failures", 0),
                metrics.get("errors", 0),
                metrics.get("skipped", 0),
                metrics.get("total_tests", 0),
                metrics.get("pass_rate", 0),
            ))
            
            # Insert component metrics
            for comp_name, comp_data in phase_data.get("components", {}).items():
                cursor.execute("""
                    INSERT INTO component_metrics (
                        run_id, phase_id, component_name,
                        coverage, warnings, failures, errors, skipped,
                        total_tests, pass_rate, test_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_data["run_id"],
                    int(phase_id),
                    comp_name,
                    comp_data.get("coverage", 0),
                    comp_data.get("warnings", 0),
                    comp_data.get("failures", 0),
                    comp_data.get("errors", 0),
                    comp_data.get("skipped", 0),
                    comp_data.get("total_tests", 0),
                    comp_data.get("pass_rate", 0),
                    comp_data.get("test_path", ""),
                ))
        
        # Insert file details
        file_details = run_data.get("file_details", {})
        for comp_name, files in file_details.items():
            for file_path, file_data in files.items():
                cursor.execute("""
                    INSERT INTO test_files (
                        run_id, component_name, file_path,
                        test_count, passed, failed, errors, skipped
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_data["run_id"],
                    comp_name,
                    file_path,
                    file_data.get("test_count", 0),
                    file_data.get("passed", 0),
                    file_data.get("failed", 0),
                    file_data.get("errors", 0),
                    file_data.get("skipped", 0),
                ))
        
        conn.commit()
        conn.close()
    
    def get_latest_run(self) -> Optional[Dict]:
        """Get the most recent run data for simulation mode."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT json_path FROM runs 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            json_path = Path(row[0])
            if json_path.exists():
                with open(json_path) as f:
                    return json.load(f)
        
        return None
    
    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get a specific run by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT json_path FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            json_path = Path(row[0])
            if json_path.exists():
                with open(json_path) as f:
                    return json.load(f)
        
        return None
    
    def list_runs(self, limit: int = 10) -> List[Dict]:
        """List recent runs with summary info."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT run_id, timestamp, duration_seconds,
                   git_branch, git_commit,
                   total_tests, overall_coverage, overall_pass_rate,
                   overall_failures, overall_errors
            FROM runs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        runs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return runs
    
    def get_latest_logs(self) -> Optional[Dict]:
        """Get the last saved test logs for bugfixing."""
        log_files = list(self.logs_dir.glob("latest_*.json"))
        if log_files:
            latest = max(log_files, key=lambda p: p.stat().st_mtime)
            with open(latest) as f:
                return json.load(f)
        return None
    
    def save_skip_events(self, run_id: str, skip_events: List[Dict]):
        """Save skip events to database for audit trail.
        
        Args:
            run_id: The run ID these events belong to
            skip_events: List of skip event dicts with test_name, component, reason, marker, etc.
        """
        if not skip_events:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for event in skip_events:
            cursor.execute("""
                INSERT INTO skip_events 
                (run_id, test_name, component, reason, marker, timestamp, phase_id, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                event.get('test_name', 'unknown'),
                event.get('component', 'unknown'),
                event.get('reason', ''),
                event.get('marker', 'skip'),
                event.get('timestamp', datetime.now(timezone.utc).isoformat()),
                event.get('phase_id'),
                event.get('file_path')
            ))
        
        conn.commit()
        conn.close()
    
    def get_skip_history(self, test_name: str = None, component: str = None, 
                         limit: int = 100) -> List[Dict]:
        """Get skip history with optional filters.
        
        Args:
            test_name: Filter by test name (exact match)
            component: Filter by component name
            limit: Max results (default 100)
        
        Returns:
            List of dicts with skip event data including frequency
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT 
                test_name,
                component,
                reason,
                marker,
                COUNT(*) as skip_count,
                MAX(timestamp) as last_seen,
                MIN(timestamp) as first_seen,
                GROUP_CONCAT(DISTINCT run_id) as run_ids
            FROM skip_events
            WHERE 1=1
        """
        params = []
        
        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)
        
        if component:
            query += " AND component = ?"
            params.append(component)
        
        query += """
            GROUP BY test_name, component, reason, marker
            ORDER BY skip_count DESC, last_seen DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def cleanup_old_runs(self, keep_days: int = 30, keep_min: int = 10):
        """Clean up old history files, keeping at least keep_min runs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get runs to keep (either recent or within keep_min)
        cursor.execute("""
            SELECT run_id, json_path, timestamp
            FROM runs
            ORDER BY timestamp DESC
        """)
        
        all_runs = cursor.fetchall()
        cutoff = datetime.now(timezone.utc).timestamp() - (keep_days * 86400)
        
        to_delete = []
        for i, (run_id, json_path, timestamp) in enumerate(all_runs):
            if i >= keep_min:  # Always keep the first keep_min runs
                try:
                    run_ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
                    if run_ts < cutoff:
                        to_delete.append((run_id, json_path))
                except Exception:
                    pass
        
        # Delete old runs
        for run_id, json_path in to_delete:
            cursor.execute("DELETE FROM skip_events WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM test_files WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM component_metrics WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM phase_metrics WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            
            if json_path:
                json_file = Path(json_path)
                if json_file.exists():
                    json_file.unlink()
        
        conn.commit()
        conn.close()
        
        return len(to_delete)


# Convenience function
def get_history_store(base_dir: str = ".ptsd") -> HistoryStore:
    """Get or create the history store instance."""
    return HistoryStore(base_dir)
