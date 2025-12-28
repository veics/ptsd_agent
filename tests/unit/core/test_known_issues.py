"""Unit tests for Known Issues Registry."""

import pytest
import tempfile
from pathlib import Path
from ptsd_agent.core.known_issues import KnownIssue, KnownIssuesRegistry


class TestKnownIssue:
    """Test KnownIssue dataclass."""
    
    def test_creation(self):
        """Test creating a valid known issue."""
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_oauth",
            reason="Known OAuth issue",
            created="2025-12-28"
        )
        assert issue.id == "TEST-1"
        assert issue.type == "failure"
        assert issue.component == "acl"
        assert issue.test_pattern == "test_oauth"
        assert issue.tags == []
    
    def test_invalid_type(self):
        """Test that invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid type"):
            KnownIssue(
                id="TEST-1",
                type="invalid",
                component="acl",
                test_pattern="test_*",
                reason="Test",
                created="2025-12-28"
            )
    
    def test_invalid_date_format(self):
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            KnownIssue(
                id="TEST-1",
                type="failure",
                component="acl",
                test_pattern="test_*",
                reason="Test",
                created="12/28/2025"  # Wrong format
            )
    
    def test_exact_match(self):
        """Test exact test name matching."""
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_oauth_flow",
            reason="Test",
            created="2025-12-28"
        )
        
        assert issue.matches("acl", "test_oauth_flow", "failure")
        assert not issue.matches("acl", "test_oauth_callback", "failure")
        assert not issue.matches("architecture", "test_oauth_flow", "failure")
        assert not issue.matches("acl", "test_oauth_flow", "error")
    
    def test_glob_pattern_matching(self):
        """Test glob pattern matching for test names."""
        issue = KnownIssue(
            id="TEST-1",
            type="warning",
            component="acl",
            test_pattern="test_oauth_*",
            reason="Test",
            created="2025-12-28"
        )
        
        assert issue.matches("acl", "test_oauth_flow", "warning")
        assert issue.matches("acl", "test_oauth_callback", "warning")
        assert issue.matches("acl", "test_oauth_anything", "warning")
        assert not issue.matches("acl", "test_permissions", "warning")


class TestKnownIssuesRegistry:
    """Test KnownIssuesRegistry."""
    
    @pytest.fixture
    def temp_registry_path(self):
        """Create a temporary registry file path."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = Path(f.name)
        yield path
        if path.exists():
            path.unlink()
    
    @pytest.fixture
    def registry(self, temp_registry_path):
        """Create a registry instance with temporary file."""
        return KnownIssuesRegistry(str(temp_registry_path))
    
    def test_empty_registry(self, registry):
        """Test creating an empty registry."""
        assert len(registry.issues) == 0
        assert registry.project_name == "PTSD Agent"
    
    def test_add_issue(self, registry):
        """Test adding a known issue."""
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_oauth",
            reason="Known issue",
            created="2025-12-28"
        )
        
        registry.add_issue(issue)
        assert len(registry.issues) == 1
        assert registry.issues[0].id == "TEST-1"
    
    def test_add_duplicate_id(self, registry):
        """Test that adding duplicate ID raises ValueError."""
        issue1 = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_oauth",
            reason="Issue 1",
            created="2025-12-28"
        )
        issue2 = KnownIssue(
            id="TEST-1",
            type="error",
            component="architecture",
            test_pattern="test_schema",
            reason="Issue 2",
            created="2025-12-28"
        )
        
        registry.add_issue(issue1)
        with pytest.raises(ValueError, match="already exists"):
            registry.add_issue(issue2)
    
    def test_remove_issue(self, registry):
        """Test removing an issue."""
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_oauth",
            reason="Test",
            created="2025-12-28"
        )
        
        registry.add_issue(issue)
        assert len(registry.issues) == 1
        
        result = registry.remove_issue("TEST-1")
        assert result is True
        assert len(registry.issues) == 0
    
    def test_remove_nonexistent(self, registry):
        """Test removing a nonexistent issue returns False."""
        result = registry.remove_issue("NONEXISTENT")
        assert result is False
    
    def test_find_matching_issue(self, registry):
        """Test finding a matching issue."""
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_oauth_*",
            reason="Test",
            created="2025-12-28"
        )
        
        registry.add_issue(issue)
        
        found = registry.find_matching_issue("acl", "test_oauth_flow", "failure")
        assert found is not None
        assert found.id == "TEST-1"
        
        not_found = registry.find_matching_issue("acl", "test_permissions", "failure")
        assert not_found is None
    
    def test_list_issues_all(self, registry):
        """Test listing all issues."""
        issue1 = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_*",
            reason="Test 1",
            created="2025-12-28"
        )
        issue2 = KnownIssue(
            id="TEST-2",
            type="error",
            component="architecture",
            test_pattern="test_*",
            reason="Test 2",
            created="2025-12-28"
        )
        
        registry.add_issue(issue1)
        registry.add_issue(issue2)
        
        all_issues = registry.list_issues()
        assert len(all_issues) == 2
    
    def test_list_issues_by_component(self, registry):
        """Test filtering issues by component."""
        issue1 = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_*",
            reason="Test 1",
            created="2025-12-28"
        )
        issue2 = KnownIssue(
            id="TEST-2",
            type="error",
            component="architecture",
            test_pattern="test_*",
            reason="Test 2",
            created="2025-12-28"
        )
        
        registry.add_issue(issue1)
        registry.add_issue(issue2)
        
        acl_issues = registry.list_issues(component="acl")
        assert len(acl_issues) == 1
        assert acl_issues[0].id == "TEST-1"
    
    def test_list_issues_by_type(self, registry):
        """Test filtering issues by type."""
        issue1 = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_*",
            reason="Test 1",
            created="2025-12-28"
        )
        issue2 = KnownIssue(
            id="TEST-2",
            type="warning",
            component="acl",
            test_pattern="test_*",
            reason="Test 2",
            created="2025-12-28"
        )
        
        registry.add_issue(issue1)
        registry.add_issue(issue2)
        
        failures = registry.list_issues(type_filter="failure")
        assert len(failures) == 1
        assert failures[0].id == "TEST-1"
    
    def test_list_issues_by_tags(self, registry):
        """Test filtering issues by tags."""
        issue1 = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_*",
            reason="Test 1",
            created="2025-12-28",
            tags=["oauth", "blocked"]
        )
        issue2 = KnownIssue(
            id="TEST-2",
            type="failure",
            component="acl",
            test_pattern="test_*",
            reason="Test 2",
            created="2025-12-28",
            tags=["permissions"]
        )
        
        registry.add_issue(issue1)
        registry.add_issue(issue2)
        
        oauth_issues = registry.list_issues(tags=["oauth"])
        assert len(oauth_issues) == 1
        assert oauth_issues[0].id == "TEST-1"
    
    def test_get_issue(self, registry):
        """Test getting a specific issue by ID."""
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_*",
            reason="Test",
            created="2025-12-28"
        )
        
        registry.add_issue(issue)
        
        found = registry.get_issue("TEST-1")
        assert found is not None
        assert found.id == "TEST-1"
        
        not_found = registry.get_issue("NONEXISTENT")
        assert not_found is None
    
    def test_count_by_type(self, registry):
        """Test counting issues by type."""
        registry.add_issue(KnownIssue(
            id="TEST-1", type="failure", component="acl",
            test_pattern="test_*", reason="Test", created="2025-12-28"
        ))
        registry.add_issue(KnownIssue(
            id="TEST-2", type="failure", component="acl",
            test_pattern="test_*", reason="Test", created="2025-12-28"
        ))
        registry.add_issue(KnownIssue(
            id="TEST-3", type="warning", component="acl",
            test_pattern="test_*", reason="Test", created="2025-12-28"
        ))
        
        counts = registry.count_by_type()
        assert counts['failure'] == 2
        assert counts['warning'] == 1
        assert counts['error'] == 0
        assert counts['skip'] == 0
    
    def test_persistence(self, temp_registry_path):
        """Test that issues persist across registry instances."""
        # Create registry and add issue
        registry1 = KnownIssuesRegistry(str(temp_registry_path))
        issue = KnownIssue(
            id="TEST-1",
            type="failure",
            component="acl",
            test_pattern="test_*",
            reason="Test",
            created="2025-12-28"
        )
        registry1.add_issue(issue)
        
        # Create new registry instance and verify issue persisted
        registry2 = KnownIssuesRegistry(str(temp_registry_path))
        assert len(registry2.issues) == 1
        assert registry2.issues[0].id == "TEST-1"
