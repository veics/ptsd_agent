"""Known Issues Registry Management.

This module provides functionality to track and manage known test failures,
allowing teams to document expected failures and filter them from diagnostic displays.

Example:
    registry = KnownIssuesRegistry()
    
    # Add a known issue
    issue = KnownIssue(
        id="JIRA-1234",
        type="failure",
        component="architecture",
        test_pattern="test_schema_validation",
        reason="Known schema mismatch, waiting for backend update",
        created="2025-12-28"
    )
    registry.add_issue(issue)
    
    # Check if a test matches a known issue
    known = registry.find_matching_issue("architecture", "test_schema_validation", "failure")
    if known:
        print(f"This is a known issue: {known.id}")
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml
import fnmatch
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class KnownIssue:
    """Represents a documented known issue.
    
    Attributes:
        id: Unique identifier (e.g., JIRA-1234, GH-567)
        type: Type of diagnostic (failure, error, warning, skip)
        component: Component name from project config
        test_pattern: Test name or glob pattern (supports *, ?, [])
        reason: Description of why this is a known issue
        created: Date documented (YYYY-MM-DD format)
        ticket_url: Optional URL to tracking ticket
        tags: Optional list of tags for filtering/organization
    """
    id: str
    type: str  # failure, error, warning, skip
    component: str
    phase_id: Optional[int] = None  # Phase number for disambiguation
    test_pattern: str = ""
    reason: str = ""
    created: str = ""
    ticket_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate field values after initialization."""
        valid_types = {'failure', 'error', 'warning', 'skip'}
        if self.type not in valid_types:
            raise ValueError(
                f"Invalid type '{self.type}'. Must be one of: {valid_types}"
            )
        
        # Validate date format
        try:
            datetime.strptime(self.created, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format '{self.created}'. Must be YYYY-MM-DD"
            )
    
    def matches(self, component: str, test_name: str, diag_type: str, phase_id: int = None) -> bool:
        """Check if this known issue matches a test diagnostic.
        
        Args:
            component: Component name from test
            test_name: Full test name (e.g., test_schema_validation)
            diag_type: Diagnostic type (failure, error, warning, skip)
            phase_id: Optional phase ID for disambiguation
        
        Returns:
            True if this known issue matches the given test
        """
        if self.component != component:
            return False
        if self.type != diag_type:
            return False
        
        # Check phase if both are specified
        if self.phase_id is not None and phase_id is not None:
            if self.phase_id != phase_id:
                return False
        
        # Use fnmatch for glob pattern matching
        # Supports: test_*, test_schema_*, test_[abc]_*
        return fnmatch.fnmatch(test_name, self.test_pattern)


class KnownIssuesRegistry:
    """Manages the known issues registry.
    
    The registry is stored in a YAML file and provides methods to:
    - Load and save issues
    - Add and remove issues
    - Find issues matching specific tests
    - List issues with filtering
    
    Example:
        registry = KnownIssuesRegistry("known_issues.yaml")
        
        # Add issue
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_oauth_*",
            reason="OAuth server unavailable",
            created="2025-12-28"
        )
        registry.add_issue(issue)
        
        # Find matching issue
        known = registry.find_matching_issue("acl", "test_oauth_flow", "failure")
        if known:
            print(f"Known issue: {known.id} - {known.reason}")
    """
    
    DEFAULT_REGISTRY_PATH = "known_issues.yaml"
    
    def __init__(self, registry_path: Optional[str] = None):
        """Initialize the known issues registry.
        
        Args:
            registry_path: Path to YAML registry file. Defaults to known_issues.yaml
                          in the current directory.
        """
        self.registry_path = Path(registry_path or self.DEFAULT_REGISTRY_PATH)
        self.issues: List[KnownIssue] = []
        self.project_name: str = "PTSD Agent"
        self._load()
    
    def _load(self) -> None:
        """Load issues from YAML file.
        
        If the file doesn't exist, starts with an empty registry.
        Logs warnings for invalid issues but continues loading valid ones.
        """
        if not self.registry_path.exists():
            logger.debug(f"Registry file not found: {self.registry_path}")
            return
        
        try:
            with open(self.registry_path) as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Empty registry file: {self.registry_path}")
                return
            
            # Load project name if present
            self.project_name = data.get('project', self.project_name)
            
            # Load issues
            for issue_data in data.get('issues', []):
                try:
                    # Convert tags to list if it's None
                    if issue_data.get('tags') is None:
                        issue_data['tags'] = []
                    
                    issue = KnownIssue(**issue_data)
                    self.issues.append(issue)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Skipping invalid issue: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.issues)} known issues from {self.registry_path}")
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse registry file: {e}")
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
    
    def save(self) -> None:
        """Save issues to YAML file.
        
        Creates the file if it doesn't exist. Updates the last_updated timestamp.
        """
        from datetime import timezone
        data = {
            'version': '1.0',
            'project': self.project_name,
            'last_updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'issues': [asdict(issue) for issue in self.issues]
        }
        
        try:
            # Ensure parent directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.registry_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Saved {len(self.issues)} known issues to {self.registry_path}")
            
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            raise
    
    def add_issue(self, issue: KnownIssue) -> None:
        """Add a new known issue to the registry.
        
        Args:
            issue: KnownIssue to add
        
        Raises:
            ValueError: If an issue with the same ID already exists
        """
        # Validate unique ID
        if any(i.id == issue.id for i in self.issues):
            raise ValueError(f"Issue ID '{issue.id}' already exists in registry")
        
        self.issues.append(issue)
        self.save()
        logger.info(f"Added known issue: {issue.id}")
    
    def bulk_add_issues(self, issues: List[KnownIssue]) -> Dict[str, Any]:
        """Add multiple known issues in bulk.
        
        Args:
            issues: List of KnownIssue objects to add
        
        Returns:
            Dictionary with 'added' count, 'skipped' count, and 'errors' list
        """
        result = {
            'added': 0,
            'skipped': 0,
            'errors': []
        }
        
        for issue in issues:
            try:
                # Check for duplicate ID
                if any(i.id == issue.id for i in self.issues):
                    result['skipped'] += 1
                    result['errors'].append(f"Duplicate ID: {issue.id}")
                    continue
                
                self.issues.append(issue)
                result['added'] += 1
            except Exception as e:
                result['errors'].append(f"Error adding {issue.id}: {str(e)}")
        
        if result['added'] > 0:
            self.save()
            logger.info(f"Bulk added {result['added']} known issues")
        
        return result
    
    def remove_issue(self, issue_id: str) -> bool:
        """Remove an issue by ID.
        
        Args:
            issue_id: ID of the issue to remove
        
        Returns:
            True if issue was found and removed, False otherwise
        """
        original_count = len(self.issues)
        self.issues = [i for i in self.issues if i.id != issue_id]
        
        if len(self.issues) < original_count:
            self.save()
            logger.info(f"Removed known issue: {issue_id}")
            return True
        
        logger.warning(f"Issue ID not found: {issue_id}")
        return False
    
    def find_matching_issue(
        self,
        component: str,
        test_name: str,
        diag_type: str
    ) -> Optional[KnownIssue]:
        """Find a known issue matching the given test diagnostic.
        
        Args:
            component: Component name
            test_name: Test name (supports glob patterns in registry)
            diag_type: Diagnostic type (failure, error, warning, skip)
        
        Returns:
            Matching KnownIssue if found, None otherwise
        """
        for issue in self.issues:
            if issue.matches(component, test_name, diag_type):
                return issue
        return None
    
    def list_issues(
        self,
        component: Optional[str] = None,
        type_filter: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[KnownIssue]:
        """List issues with optional filtering.
        
        Args:
            component: Filter by component name
            type_filter: Filter by type (failure, error, warning, skip)
            tags: Filter by tags (issues must have ALL specified tags)
        
        Returns:
            List of matching KnownIssues
        """
        filtered = self.issues
        
        if component:
            filtered = [i for i in filtered if i.component == component]
        
        if type_filter:
            filtered = [i for i in filtered if i.type == type_filter]
        
        if tags:
            filtered = [
                i for i in filtered
                if all(tag in i.tags for tag in tags)
            ]
        
        return filtered
    
    def get_issue(self, issue_id: str) -> Optional[KnownIssue]:
        """Get a specific issue by ID.
        
        Args:
            issue_id: ID of the issue to retrieve
        
        Returns:
            KnownIssue if found, None otherwise
        """
        for issue in self.issues:
            if issue.id == issue_id:
                return issue
        return None
    
    def count_by_type(self) -> Dict[str, int]:
        """Count issues grouped by type.
        
        Returns:
            Dictionary mapping type to count
        """
        counts = {'failure': 0, 'error': 0, 'warning': 0, 'skip': 0}
        for issue in self.issues:
            counts[issue.type] = counts.get(issue.type, 0) + 1
        return counts
