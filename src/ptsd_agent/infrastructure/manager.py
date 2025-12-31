"""Infrastructure Manager for PTSD Agent.

Orchestrates the complete infrastructure setup process:
1. Install dependencies
2. Start Docker containers
3. Wait for health checks
4. Run database migrations
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from .dependencies import DependencyInstaller, InstallResult
from .docker import DockerManager, DockerResult
from .migrations import MigrationRunner, MigrationResult

logger = logging.getLogger(__name__)


class InfrastructurePhase(Enum):
    """Phases of infrastructure setup."""
    DEPENDENCIES = "dependencies"
    DOCKER = "docker"
    HEALTH_CHECK = "health_check"
    MIGRATIONS = "migrations"
    COMPLETE = "complete"


@dataclass
class InfrastructureConfig:
    """Configuration for infrastructure setup."""
    enabled: bool = False  # Opt-in by default
    
    # Dependencies - DISABLED by default (too slow for regular runs)
    auto_install_dependencies: bool = False
    requirements_files: List[str] = field(default_factory=lambda: ["requirements.txt"])
    dependency_timeout: int = 300
    
    # Docker - enabled when infrastructure is enabled
    docker_enabled: bool = True
    compose_file: Optional[str] = None
    docker_services: Optional[List[str]] = None
    startup_timeout: int = 60
    health_check_interval: int = 2
    
    # Migrations - enabled when infrastructure is enabled
    migrations_enabled: bool = True
    migration_tool: str = "alembic"
    migration_timeout: int = 120
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InfrastructureConfig":
        """Create config from dictionary (e.g., from YAML).
        
        If no infrastructure section exists, returns defaults (disabled).
        """
        if not data:
            return cls()
        
        infra = data.get("infrastructure", {})
        
        # If no infrastructure config, return defaults (disabled)
        if not infra:
            return cls()
        
        deps = infra.get("dependencies", {})
        docker = infra.get("docker", {})
        migrations = infra.get("migrations", {})
        
        return cls(
            # Only enable if explicitly set in config
            enabled=infra.get("enabled", False),
            auto_install_dependencies=deps.get("auto_install", False),
            requirements_files=deps.get("requirements_files", ["requirements.txt"]),
            dependency_timeout=deps.get("timeout", 300),
            docker_enabled=docker.get("enabled", True),
            compose_file=docker.get("compose_file"),
            docker_services=docker.get("services"),
            startup_timeout=docker.get("startup_timeout", 60),
            health_check_interval=docker.get("health_check_interval", 2),
            migrations_enabled=migrations.get("enabled", True),
            migration_tool=migrations.get("tool", "alembic"),
            migration_timeout=migrations.get("timeout", 120),
        )


@dataclass 
class InfrastructureResult:
    """Result of complete infrastructure setup."""
    success: bool
    phase: InfrastructurePhase
    dependencies: Optional[InstallResult] = None
    docker: Optional[DockerResult] = None
    migrations: Optional[MigrationResult] = None
    error_message: Optional[str] = None
    
    @property
    def summary(self) -> str:
        """Generate human-readable summary."""
        parts = []
        
        if self.dependencies and self.dependencies.success:
            parts.append(f"✓ {self.dependencies.packages_installed} packages installed")
        
        if self.docker and self.docker.success:
            container_count = len(self.docker.containers)
            parts.append(f"✓ {container_count} containers running")
        
        if self.migrations and self.migrations.success:
            if self.migrations.migrations_applied > 0:
                parts.append(f"✓ {self.migrations.migrations_applied} migrations applied")
            else:
                parts.append("✓ Database ready")
        
        if not parts:
            return "No infrastructure setup required"
        
        return " | ".join(parts)


class InfrastructureManager:
    """Orchestrates infrastructure setup for PTSD Agent.
    
    This is the main entry point for infrastructure initialization.
    It coordinates dependency installation, Docker container startup,
    health checks, and database migrations.
    """
    
    def __init__(
        self,
        project_root: str,
        config: Optional[InfrastructureConfig] = None,
        progress_callback: Optional[Callable[[InfrastructurePhase, str, float], None]] = None
    ):
        """Initialize infrastructure manager.
        
        Args:
            project_root: Root directory of the project
            config: Optional configuration (uses defaults if None)
            progress_callback: Optional callback(phase, message, progress) for UI
        """
        self.project_root = Path(project_root)
        self.config = config or InfrastructureConfig()
        self.progress_callback = progress_callback
        
        # Initialize sub-managers
        self.dependency_installer = DependencyInstaller(
            project_root=str(self.project_root),
            timeout=self.config.dependency_timeout,
            progress_callback=self._make_phase_callback(InfrastructurePhase.DEPENDENCIES)
        )
        
        self.docker_manager = DockerManager(
            project_root=str(self.project_root),
            compose_file=self.config.compose_file,
            startup_timeout=self.config.startup_timeout,
            health_check_interval=self.config.health_check_interval,
            progress_callback=self._make_phase_callback(InfrastructurePhase.DOCKER)
        )
        
        self.migration_runner = MigrationRunner(
            project_root=str(self.project_root),
            tool=self.config.migration_tool,
            timeout=self.config.migration_timeout,
            progress_callback=self._make_phase_callback(InfrastructurePhase.MIGRATIONS)
        )
    
    def _make_phase_callback(self, phase: InfrastructurePhase):
        """Create a progress callback for a specific phase."""
        def callback(message: str, progress: float):
            if self.progress_callback:
                self.progress_callback(phase, message, progress)
        return callback
    
    def _emit_progress(self, phase: InfrastructurePhase, message: str, progress: float = 0.0):
        """Emit progress update."""
        if self.progress_callback:
            self.progress_callback(phase, message, progress)
        logger.info(f"[Infrastructure:{phase.value}] {message}")
    
    def setup(self, service_paths: Optional[List[str]] = None) -> InfrastructureResult:
        """Run complete infrastructure setup.
        
        Args:
            service_paths: Optional list of specific service directories
            
        Returns:
            InfrastructureResult with setup status
        """
        if not self.config.enabled:
            return InfrastructureResult(
                success=True,
                phase=InfrastructurePhase.COMPLETE
            )
        
        deps_result = None
        docker_result = None
        migrations_result = None
        
        # Phase 1: Install dependencies
        if self.config.auto_install_dependencies:
            self._emit_progress(InfrastructurePhase.DEPENDENCIES, "Installing dependencies...", 0.0)
            deps_result = self.dependency_installer.install_all(service_paths)
            
            if not deps_result.success:
                return InfrastructureResult(
                    success=False,
                    phase=InfrastructurePhase.DEPENDENCIES,
                    dependencies=deps_result,
                    error_message=f"Dependency installation failed: {deps_result.error_message}"
                )
        
        # Phase 2: Start Docker containers
        if self.config.docker_enabled:
            self._emit_progress(InfrastructurePhase.DOCKER, "Starting containers...", 0.0)
            docker_result = self.docker_manager.start_containers(self.config.docker_services)
            
            if not docker_result.success:
                return InfrastructureResult(
                    success=False,
                    phase=InfrastructurePhase.DOCKER,
                    dependencies=deps_result,
                    docker=docker_result,
                    error_message=f"Docker startup failed: {docker_result.error_message}"
                )
        
        # Phase 3: Run migrations
        if self.config.migrations_enabled:
            self._emit_progress(InfrastructurePhase.MIGRATIONS, "Running migrations...", 0.0)
            
            if service_paths:
                migrations_result = self.migration_runner.run_for_services(service_paths)
            else:
                # Find services with migrations
                services_with_migrations = self._find_services_with_migrations()
                if services_with_migrations:
                    migrations_result = self.migration_runner.run_for_services(services_with_migrations)
                else:
                    migrations_result = MigrationResult(success=True, details=["No migrations found"])
            
            if not migrations_result.success:
                return InfrastructureResult(
                    success=False,
                    phase=InfrastructurePhase.MIGRATIONS,
                    dependencies=deps_result,
                    docker=docker_result,
                    migrations=migrations_result,
                    error_message=f"Migrations failed: {migrations_result.error_message}"
                )
        
        self._emit_progress(InfrastructurePhase.COMPLETE, "Infrastructure ready", 1.0)
        
        return InfrastructureResult(
            success=True,
            phase=InfrastructurePhase.COMPLETE,
            dependencies=deps_result,
            docker=docker_result,
            migrations=migrations_result
        )
    
    def _find_services_with_migrations(self) -> List[str]:
        """Find all service directories that have migrations."""
        services = []
        
        services_dir = self.project_root / "services"
        if services_dir.exists():
            for service_path in services_dir.iterdir():
                if service_path.is_dir():
                    migrations_dir = self.migration_runner.find_migration_directory(str(service_path))
                    if migrations_dir:
                        services.append(str(service_path))
        
        return services
    
    def teardown(self, remove_volumes: bool = False) -> DockerResult:
        """Stop infrastructure (containers, etc.).
        
        Args:
            remove_volumes: Also remove Docker volumes
            
        Returns:
            DockerResult indicating success
        """
        if self.config.docker_enabled:
            return self.docker_manager.stop_containers(remove_volumes=remove_volumes)
        
        return DockerResult(success=True)
    
    def check_status(self) -> Dict[str, Any]:
        """Check current infrastructure status.
        
        Returns:
            Dictionary with status of each component
        """
        status = {
            "docker_available": self.docker_manager.is_docker_available(),
            "containers": [],
            "compose_file": str(self.docker_manager.compose_file) if self.docker_manager.compose_file else None,
        }
        
        if status["docker_available"]:
            containers = self.docker_manager.get_running_containers()
            status["containers"] = [
                {"name": c.name, "running": c.running, "healthy": c.healthy}
                for c in containers
            ]
        
        return status
