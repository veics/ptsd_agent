"""MCP tools for known issues registry management."""

from typing import Dict, Any, List, Optional
from ptsd_agent.core.known_issues import KnownIssue, KnownIssuesRegistry
import logging

logger = logging.getLogger(__name__)


def document_known_issue(
    issue_id: str,
    type: str,
    component: str,
    test_pattern: str,
    reason: str,
    ticket_url: Optional[str] = None,
    tags: Optional[List[str]] = None,
    created: Optional[str] = None
) -> Dict[str, Any]:
    """Document a new known issue.
    
    Args:
        issue_id: Unique identifier (e.g., JIRA-1234, GH-567)
        type: Type of issue (failure, error, warning, skip)
        component: Component name from project config
        test_pattern: Test name or glob pattern (supports *, ?, [])
        reason: Description of why this is a known issue
        ticket_url: Optional URL to tracking ticket
        tags: Optional list of tags for filtering
        created: Optional creation date (YYYY-MM-DD), defaults to today
    
    Returns:
        Dict with status and message
        
    Example:
        result = document_known_issue(
            issue_id="JIRA-1234",
            type="failure",
            component="architecture",
            test_pattern="test_schema_validation",
            reason="Known schema mismatch, blocked on backend update"
        )
    """
    try:
        # Use current date if not provided
        if created is None:
            from datetime import datetime
            created = datetime.now().strftime("%Y-%m-%d")
        
        # Create known issue
        issue = KnownIssue(
            id=issue_id,
            type=type,
            component=component,
            test_pattern=test_pattern,
            reason=reason,
            created=created,
            ticket_url=ticket_url,
            tags=tags or []
        )
        
        # Add to registry
        registry = KnownIssuesRegistry()
        registry.add_issue(issue)
        
        logger.info(f"Documented known issue: {issue_id}")
        
        return {
            'status': 'success',
            'message': f"Known issue '{issue_id}' documented successfully",
            'issue': {
                'id': issue.id,
                'type': issue.type,
                'component': issue.component,
                'test_pattern': issue.test_pattern,
                'reason': issue.reason
            }
        }
        
    except ValueError as e:
        logger.error(f"Failed to document known issue: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error documenting known issue: {e}")
        return {
            'status': 'error',
            'message': f"Unexpected error: {str(e)}"
        }


def remove_known_issue(issue_id: str) -> Dict[str, Any]:
    """Remove a known issue from the registry.
    
    Args:
        issue_id: ID of issue to remove
    
    Returns:
        Dict with status and message
        
    Example:
        result = remove_known_issue("JIRA-1234")
    """
    try:
        registry = KnownIssuesRegistry()
        success = registry.remove_issue(issue_id)
        
        if success:
            logger.info(f"Removed known issue: {issue_id}")
            return {
                'status': 'success',
                'message': f"Known issue '{issue_id}' removed successfully"
            }
        else:
            return {
                'status': 'error',
                'message': f"Issue ID '{issue_id}' not found in registry"
            }
            
    except Exception as e:
        logger.error(f"Error removing known issue: {e}")
        return {
            'status': 'error',
            'message': f"Error: {str(e)}"
        }


def list_known_issues(
    component: Optional[str] = None,
    type_filter: Optional[str] = None,
    tags: Optional[List[str]] = None,
    format: str = "summary"
) -> Dict[str, Any]:
    """List known issues with optional filtering.
    
    Args:
        component: Optional component filter
        type_filter: Optional type filter (failure, error, warning, skip)
        tags: Optional tags filter (issues must have ALL specified tags)
        format: Output format - "summary" (default) or "detailed"
    
    Returns:
        Dict with status, count, and issues list
        
    Example:
        result = list_known_issues(component="acl", type_filter="failure")
    """
    try:
        registry = KnownIssuesRegistry()
        issues = registry.list_issues(
            component=component,
            type_filter=type_filter,
            tags=tags
        )
        
        if format == "detailed":
            issues_data = [
                {
                    'id': issue.id,
                    'type': issue.type,
                    'component': issue.component,
                    'test_pattern': issue.test_pattern,
                    'reason': issue.reason,
                    'created': issue.created,
                    'ticket_url': issue.ticket_url,
                    'tags': issue.tags
                }
                for issue in issues
            ]
        else:  # summary format
            issues_data = [
                {
                    'id': issue.id,
                    'type': issue.type,
                    'component': issue.component,
                    'pattern': issue.test_pattern
                }
                for issue in issues
            ]
        
        # Build filter description
        filters = []
        if component:
            filters.append(f"component={component}")
        if type_filter:
            filters.append(f"type={type_filter}")
        if tags:
            filters.append(f"tags={','.join(tags)}")
        filter_desc = f" (filters: {', '.join(filters)})" if filters else ""
        
        return {
            'status': 'success',
            'count': len(issues),
            'message': f"Found {len(issues)} known issue(s){filter_desc}",
            'issues': issues_data
        }
        
    except Exception as e:
        logger.error(f"Error listing known issues: {e}")
        return {
            'status': 'error',
            'message': f"Error: {str(e)}",
            'count': 0,
            'issues': []
        }


def get_known_issue_stats() -> Dict[str, Any]:
    """Get statistics about known issues in the registry.
    
    Returns:
        Dict with counts by type and component
        
    Example:
        stats = get_known_issue_stats()
        print(f"Total failures: {stats['by_type']['failure']}")
    """
    try:
        registry = KnownIssuesRegistry()
        
        # Count by type
        type_counts = registry.count_by_type()
        
        # Count by component
        component_counts = {}
        for issue in registry.issues:
            component_counts[issue.component] = component_counts.get(issue.component, 0) + 1
        
        return {
            'status': 'success',
            'total': len(registry.issues),
            'by_type': type_counts,
            'by_component': component_counts
        }
        
    except Exception as e:
        logger.error(f"Error getting known issue stats: {e}")
        return {
            'status': 'error',
            'message': f"Error: {str(e)}",
            'total': 0,
            'by_type': {},
            'by_component': {}
        }
