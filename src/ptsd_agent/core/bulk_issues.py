"""Bulk documentation for known issues from YAML file.

Example bulk_issues.yaml:
---
issues:
  - id: JIRA-1234
    type: failure
    component: acl
    phase_id: 1
    test_pattern: 'test_oauth_*'
    reason: 'OAuth server unavailable in CI'
    ticket_url: 'https://jira.com/1234'
    tags: ['oauth', 'ci-only']
    
  - id: JIRA-1235
    type: error
    component: auth
    phase_id: 2
    test_pattern: 'test_token_*'
    reason: 'Known token expiry issue'
    tags: ['auth']
"""

from pathlib import Path
from typing import List
import yaml
from datetime import datetime

from ptsd_agent.core.known_issues import KnownIssue, KnownIssuesRegistry


def load_bulk_issues_from_yaml(yaml_path: str) -> List[KnownIssue]:
    """Load multiple known issues from YAML file.
    
    Args:
        yaml_path: Path to YAML file containing issues list
    
    Returns:
        List of KnownIssue objects
    
    Raises:
        FileNotFoundError: If yaml_path doesn't exist
        ValueError: If YAML is invalid
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Bulk issues file not found: {yaml_path}")
    
    with open(path) as f:
        data = yaml.safe_load(f)
    
    if not data or 'issues' not in data:
        raise ValueError("YAML must contain 'issues' list")
    
    issues = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for issue_data in data['issues']:
        # Set defaults
        if 'created' not in issue_data:
            issue_data['created'] = today
        if 'tags' not in issue_data:
            issue_data['tags'] = []
        
        try:
            issue = KnownIssue(**issue_data)
            issues.append(issue)
        except (TypeError, ValueError) as e:
            print(f"Warning: Skipping invalid issue: {e}")
            continue
    
    return issues


def bulk_document_issues(registry: KnownIssuesRegistry, yaml_path: str) -> dict:
    """Document multiple known issues from YAML file.
    
    Args:
        registry: KnownIssuesRegistry instance
        yaml_path: Path to bulk issues YAML file
    
    Returns:
        Dictionary with added, skipped counts and errors
    """
    issues = load_bulk_issues_from_yaml(yaml_path)
    result = registry.bulk_add_issues(issues)
    
    # Print summary
    print(f"\nBulk Documentation Summary:")
    print(f"  Added: {result['added']}")
    print(f"  Skipped: {result['skipped']}")
    
    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    return result
