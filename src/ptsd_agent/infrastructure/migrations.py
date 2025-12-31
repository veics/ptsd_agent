"""Migration Runner for PTSD Agent.

Runs database migrations (Alembic, Django, etc.) before tests.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of migration operations."""
    success: bool
    migrations_applied: int = 0
    error_message: Optional[str] = None
    details: List[str] = field(default_factory=list)


class MigrationRunner:
    """Runs database migrations for test environments.
    
    Supports:
    - Alembic (SQLAlchemy)
    - Django migrations
    - Custom migration scripts
    """
    
    def __init__(
        self,
        project_root: str,
        tool: str = "alembic",
        timeout: int = 120,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """Initialize migration runner.
        
        Args:
            project_root: Root directory of the project
            tool: Migration tool to use ("alembic", "django", "custom")
            timeout: Maximum time for migrations in seconds
            progress_callback: Optional callback for UI updates
        """
        self.project_root = Path(project_root)
        self.tool = tool.lower()
        self.timeout = timeout
        self.progress_callback = progress_callback
    
    def _emit_progress(self, message: str, progress: float = 0.0):
        """Emit progress update to callback if registered."""
        if self.progress_callback:
            self.progress_callback(message, progress)
        logger.debug(f"[MigrationRunner] {message} ({progress:.0%})")
    
    def find_migration_directory(self, service_path: Optional[str] = None) -> Optional[Path]:
        """Find migrations directory.
        
        Args:
            service_path: Optional service-specific path
            
        Returns:
            Path to migrations directory or None
        """
        search_path = Path(service_path) if service_path else self.project_root
        
        # Common migration directory names
        candidates = [
            "migrations",
            "alembic",
            "db/migrations",
        ]
        
        for candidate in candidates:
            path = search_path / candidate
            if path.exists() and path.is_dir():
                return path
        
        return None
    
    def get_python_executable(self, service_path: Optional[str] = None) -> str:
        """Get Python executable for running migrations."""
        import sys
        
        if service_path:
            service_path = Path(service_path)
            for venv_name in [".venv", "venv"]:
                venv_python = service_path / venv_name / "bin" / "python"
                if venv_python.exists():
                    return str(venv_python)
        
        for venv_name in [".venv", "venv"]:
            venv_python = self.project_root / venv_name / "bin" / "python"
            if venv_python.exists():
                return str(venv_python)
        
        return sys.executable
    
    def check_migration_status(self, service_path: Optional[str] = None) -> tuple:
        """Check current migration status.
        
        Returns:
            Tuple of (current_revision, head_revision, pending_count)
        """
        cwd = Path(service_path) if service_path else self.project_root
        python_exe = self.get_python_executable(service_path)
        
        if self.tool == "alembic":
            try:
                # Get current revision
                result = subprocess.run(
                    [python_exe, "-m", "alembic", "current"],
                    capture_output=True,
                    text=True,
                    cwd=str(cwd),
                    timeout=30
                )
                current = result.stdout.strip().split('\n')[0] if result.returncode == 0 else None
                
                # Get head revision
                result = subprocess.run(
                    [python_exe, "-m", "alembic", "heads"],
                    capture_output=True,
                    text=True,
                    cwd=str(cwd),
                    timeout=30
                )
                head = result.stdout.strip().split('\n')[0] if result.returncode == 0 else None
                
                # Count pending migrations
                result = subprocess.run(
                    [python_exe, "-m", "alembic", "history", "-r", "current:head"],
                    capture_output=True,
                    text=True,
                    cwd=str(cwd),
                    timeout=30
                )
                pending = len([l for l in result.stdout.strip().split('\n') if l.strip()]) if result.returncode == 0 else 0
                
                return current, head, pending
                
            except Exception as e:
                logger.warning(f"Failed to check migration status: {e}")
                return None, None, 0
        
        return None, None, 0
    
    def run_migrations(
        self,
        service_path: Optional[str] = None,
        revision: str = "head"
    ) -> MigrationResult:
        """Run migrations to specified revision.
        
        Args:
            service_path: Optional service-specific path
            revision: Target revision (default: "head" for latest)
            
        Returns:
            MigrationResult with migration status
        """
        cwd = Path(service_path) if service_path else self.project_root
        python_exe = self.get_python_executable(service_path)
        
        # Check if migrations directory exists
        migrations_dir = self.find_migration_directory(service_path)
        if not migrations_dir:
            return MigrationResult(
                success=True,
                details=["No migrations directory found - skipping"]
            )
        
        self._emit_progress(f"Running migrations in {cwd.name}...", 0.2)
        
        if self.tool == "alembic":
            return self._run_alembic(cwd, python_exe, revision)
        elif self.tool == "django":
            return self._run_django(cwd, python_exe)
        else:
            return MigrationResult(
                success=False,
                error_message=f"Unknown migration tool: {self.tool}"
            )
    
    def _run_alembic(self, cwd: Path, python_exe: str, revision: str = "head") -> MigrationResult:
        """Run Alembic migrations."""
        try:
            # First, try to create tables if DB is empty
            result = subprocess.run(
                [python_exe, "-m", "alembic", "upgrade", revision],
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                # Count applied migrations from output
                applied = result.stdout.count("Running upgrade")
                self._emit_progress(f"Applied {applied} migrations", 1.0)
                
                return MigrationResult(
                    success=True,
                    migrations_applied=applied,
                    details=[result.stdout] if result.stdout else []
                )
            else:
                # Check if it's a "database doesn't exist" error
                if "database" in result.stderr.lower() and "not exist" in result.stderr.lower():
                    return MigrationResult(
                        success=False,
                        error_message="Database does not exist. Start containers first.",
                        details=[result.stderr]
                    )
                
                return MigrationResult(
                    success=False,
                    error_message=result.stderr[:500],
                    details=[result.stderr]
                )
                
        except subprocess.TimeoutExpired:
            return MigrationResult(
                success=False,
                error_message=f"Migrations timed out after {self.timeout}s"
            )
        except Exception as e:
            return MigrationResult(
                success=False,
                error_message=str(e)
            )
    
    def _run_django(self, cwd: Path, python_exe: str) -> MigrationResult:
        """Run Django migrations."""
        try:
            result = subprocess.run(
                [python_exe, "manage.py", "migrate", "--noinput"],
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                applied = result.stdout.count("Applying")
                return MigrationResult(
                    success=True,
                    migrations_applied=applied,
                    details=[result.stdout] if result.stdout else []
                )
            else:
                return MigrationResult(
                    success=False,
                    error_message=result.stderr[:500],
                    details=[result.stderr]
                )
                
        except subprocess.TimeoutExpired:
            return MigrationResult(
                success=False,
                error_message=f"Migrations timed out after {self.timeout}s"
            )
        except Exception as e:
            return MigrationResult(
                success=False,
                error_message=str(e)
            )
    
    def run_for_services(self, service_paths: List[str]) -> MigrationResult:
        """Run migrations for multiple services.
        
        Args:
            service_paths: List of service directories
            
        Returns:
            Aggregated MigrationResult
        """
        total_applied = 0
        all_details = []
        errors = []
        
        for i, service_path in enumerate(service_paths):
            progress = (i + 1) / len(service_paths)
            self._emit_progress(f"Migrating {Path(service_path).name}", progress * 0.9)
            
            result = self.run_migrations(service_path)
            
            if result.success:
                total_applied += result.migrations_applied
                all_details.extend(result.details)
            else:
                errors.append(f"{Path(service_path).name}: {result.error_message}")
        
        self._emit_progress("Migrations complete", 1.0)
        
        return MigrationResult(
            success=len(errors) == 0,
            migrations_applied=total_applied,
            error_message="; ".join(errors) if errors else None,
            details=all_details
        )
