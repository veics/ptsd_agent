"""Docker Manager for PTSD Agent.

Manages Docker containers required for testing, including startup,
health checks, and cleanup.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ContainerStatus:
    """Status of a Docker container."""
    name: str
    running: bool
    healthy: bool = False
    port: Optional[int] = None
    error: Optional[str] = None


@dataclass
class DockerResult:
    """Result of Docker operations."""
    success: bool
    containers: List[ContainerStatus] = field(default_factory=list)
    error_message: Optional[str] = None


class DockerManager:
    """Manages Docker containers for test infrastructure.
    
    Supports:
    - docker-compose for multi-container setups
    - Health check polling
    - Container lifecycle management
    """
    
    def __init__(
        self,
        project_root: str,
        compose_file: Optional[str] = None,
        startup_timeout: int = 60,
        health_check_interval: int = 2,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """Initialize Docker manager.
        
        Args:
            project_root: Root directory of the project
            compose_file: Path to docker-compose file (auto-detect if None)
            startup_timeout: Max seconds to wait for containers to be healthy
            health_check_interval: Seconds between health checks
            progress_callback: Optional callback(message, progress_pct) for UI updates
        """
        self.project_root = Path(project_root)
        self.compose_file = self._find_compose_file(compose_file)
        self.startup_timeout = startup_timeout
        self.health_check_interval = health_check_interval
        self.progress_callback = progress_callback
    
    def _emit_progress(self, message: str, progress: float = 0.0):
        """Emit progress update to callback if registered."""
        if self.progress_callback:
            self.progress_callback(message, progress)
        logger.debug(f"[DockerManager] {message} ({progress:.0%})")
    
    def _find_compose_file(self, specified: Optional[str] = None) -> Optional[Path]:
        """Find docker-compose file.
        
        Args:
            specified: Explicitly specified compose file path
            
        Returns:
            Path to compose file or None if not found
        """
        if specified:
            path = Path(specified)
            if path.is_absolute():
                return path if path.exists() else None
            return self.project_root / specified if (self.project_root / specified).exists() else None
        
        # Auto-detect common compose file names
        candidates = [
            "docker-compose.test.yml",
            "docker-compose.test.yaml",
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]
        
        for candidate in candidates:
            path = self.project_root / candidate
            if path.exists():
                return path
        
        return None
    
    def is_docker_available(self) -> bool:
        """Check if Docker is installed and running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_running_containers(self) -> List[ContainerStatus]:
        """Get list of currently running containers for this project."""
        if not self.compose_file:
            return []
        
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(self.compose_file), "ps", "--format", "json"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=30
            )
            
            if result.returncode != 0:
                return []
            
            # Parse JSON output
            import json
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        containers.append(ContainerStatus(
                            name=data.get('Service', data.get('Name', 'unknown')),
                            running=data.get('State', '').lower() == 'running',
                            healthy='healthy' in data.get('Health', '').lower() if data.get('Health') else True
                        ))
                    except json.JSONDecodeError:
                        continue
            
            return containers
            
        except Exception as e:
            logger.warning(f"Failed to get running containers: {e}")
            return []
    
    def start_containers(self, services: Optional[List[str]] = None) -> DockerResult:
        """Start Docker containers using docker-compose.
        
        Args:
            services: Optional list of specific services to start
            
        Returns:
            DockerResult with container statuses
        """
        if not self.is_docker_available():
            return DockerResult(
                success=False,
                error_message="Docker is not available. Please install Docker and ensure it's running."
            )
        
        if not self.compose_file:
            return DockerResult(
                success=False,
                error_message="No docker-compose file found in project"
            )
        
        self._emit_progress("Starting Docker containers...", 0.1)
        
        # Build docker-compose up command
        cmd = [
            "docker", "compose",
            "-f", str(self.compose_file),
            "up", "-d",
            "--wait",  # Wait for containers to be healthy
        ]
        
        if services:
            cmd.extend(services)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=self.startup_timeout
            )
            
            if result.returncode != 0:
                return DockerResult(
                    success=False,
                    error_message=f"docker-compose up failed: {result.stderr[:500]}"
                )
            
            self._emit_progress("Containers started, checking health...", 0.5)
            
            # Wait for health checks
            healthy = self._wait_for_healthy()
            
            containers = self.get_running_containers()
            
            self._emit_progress("Containers ready", 1.0)
            
            return DockerResult(
                success=healthy,
                containers=containers,
                error_message=None if healthy else "Some containers failed health checks"
            )
            
        except subprocess.TimeoutExpired:
            return DockerResult(
                success=False,
                error_message=f"Container startup timed out after {self.startup_timeout}s"
            )
        except Exception as e:
            return DockerResult(
                success=False,
                error_message=str(e)
            )
    
    def _wait_for_healthy(self) -> bool:
        """Wait for all containers to be healthy.
        
        Returns:
            True if all containers are healthy within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.startup_timeout:
            containers = self.get_running_containers()
            
            if not containers:
                time.sleep(self.health_check_interval)
                continue
            
            all_healthy = all(c.running and c.healthy for c in containers)
            
            if all_healthy:
                return True
            
            elapsed = time.time() - start_time
            progress = 0.5 + (elapsed / self.startup_timeout) * 0.4
            self._emit_progress(f"Waiting for containers... ({int(elapsed)}s)", progress)
            
            time.sleep(self.health_check_interval)
        
        return False
    
    def stop_containers(self, remove_volumes: bool = False) -> DockerResult:
        """Stop and optionally remove Docker containers.
        
        Args:
            remove_volumes: Also remove volumes
            
        Returns:
            DockerResult indicating success/failure
        """
        if not self.compose_file:
            return DockerResult(success=True)
        
        cmd = ["docker", "compose", "-f", str(self.compose_file), "down"]
        
        if remove_volumes:
            cmd.append("-v")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=60
            )
            
            return DockerResult(
                success=result.returncode == 0,
                error_message=result.stderr if result.returncode != 0 else None
            )
            
        except Exception as e:
            return DockerResult(
                success=False,
                error_message=str(e)
            )
    
    def check_service_health(self, service: str, port: int, timeout: int = 5) -> bool:
        """Check if a specific service is responding.
        
        Args:
            service: Service name
            port: Port to check
            timeout: Connection timeout
            
        Returns:
            True if service is responding
        """
        import socket
        
        try:
            with socket.create_connection(("localhost", port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
