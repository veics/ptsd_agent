"""Stub status logic functions for backward compatibility."""

def determine_component_status(has_tests=False, metrics=None, tm_status=None):
    """Determine component status from metrics and task master status."""
    if has_tests:
        if metrics and metrics.get('pass_rate', 0) >= 100:
            return "complete"
        elif metrics and metrics.get('total_tests', 0) > 0:
            return "in progress"
        else:
            return "in progress"
    else:
        # No tests - use task master status
        if tm_status == "completed":
            return "complete"
        elif tm_status in ["in-progress", "ready"]:
            return "in progress"
        else:
            return "planned"


def determine_phase_status(component_statuses):
    """Determine phase status from component statuses."""
    if not component_statuses:
        return "not planned"
    
    if all(s == "complete" for s in component_statuses):
        return "complete"
    elif any(s in ["in progress", "complete"] for s in component_statuses):
        return "in progress"
    else:
        return "planned"
