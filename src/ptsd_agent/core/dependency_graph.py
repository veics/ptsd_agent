"""Dependency graph analyzer for cross-phase dependencies.

Detects circular dependencies and provides execution order recommendations.
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque


class DependencyGraph:
    """Analyzes and visualizes component/phase dependencies."""
    
    def __init__(self):
        """Initialize dependency graph."""
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)
    
    def add_dependency(self, node: str, depends_on: str):
        """Add a dependency edge.
        
        Args:
            node: The dependent node
            depends_on: The node that must complete first
        """
        self.nodes.add(node)
        self.nodes.add(depends_on)
        self.edges[node].append(depends_on)
        self.reverse_edges[depends_on].append(node)
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies using DFS.
        
        Returns:
            List of cycles found, each cycle is a list of nodes
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            """DFS to detect cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in self.nodes:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def topological_sort(self) -> Optional[List[str]]:
        """Get topological sort (execution order).
        
        Returns:
            Ordered list of nodes, or None if cycles exist
        """
        # Check for cycles first
        if self.detect_cycles():
            return None
        
        # Kahn's algorithm
        in_degree = {node: 0 for node in self.nodes}
        for node in self.nodes:
            for dep in self.edges.get(node, []):
                in_degree[node] += 1
        
        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for dependent in self.reverse_edges.get(node, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return result if len(result) == len(self.nodes) else None
    
    def visualize(self, max_width: int = 80) -> List[str]:
        """Generate ASCII tree visualization.
        
        Args:
            max_width: Maximum width for output
        
        Returns:
            List of strings representing the tree
        """
        lines = []
        lines.append("Dependency Graph")
        lines.append("=" * min(max_width, 40))
        lines.append("")
        
        # Get roots (nodes with no dependencies)
        roots = [node for node in self.nodes if not self.edges.get(node)]
        
        if not roots:
            lines.append("⚠ No root nodes found (possible cycle)")
            return lines
        
        visited = set()
        
        def render_node(node: str, indent: str = "", is_last: bool = True):
            """Recursively render node and children."""
            if node in visited:
                lines.append(f"{indent}{'└─' if is_last else '├─'} {node} [CYCLE]")
                return
            
            visited.add(node)
            lines.append(f"{indent}{'└─' if is_last else '├─'} {node}")
            
            dependents = self.reverse_edges.get(node, [])
            for i, dep in enumerate(dependents):
                is_last_child = (i == len(dependents) - 1)
                new_indent = indent + ("   " if is_last else "│  ")
                render_node(dep, new_indent, is_last_child)
        
        for i, root in enumerate(roots):
            render_node(root, "", i == len(roots) - 1)
            if i < len(roots) - 1:
                lines.append("")
        
        return lines
    
    def get_blocked_by(self, node: str, failed_nodes: Set[str]) -> List[str]:
        """Get list of failed dependencies blocking this node.
        
        Args:
            node: Node to check
            failed_nodes: Set of nodes that have failed
        
        Returns:
            List of failed dependencies blocking this node
        """
        blockers = []
        
        def check_dependencies(n: str, visited: Set[str]):
            """Recursively check all dependencies."""
            if n in visited:
                return
            visited.add(n)
            
            for dep in self.edges.get(n, []):
                if dep in failed_nodes:
                    blockers.append(dep)
                check_dependencies(dep, visited)
        
        check_dependencies(node, set())
        return blockers


def build_dependency_graph_from_config(config: Dict) -> DependencyGraph:
    """Build dependency graph from .ptsd.yaml config.
    
    Args:
        config: Parsed .ptsd.yaml configuration
    
    Returns:
        DependencyGraph instance
    """
    graph = DependencyGraph()
    
    # Add phase dependencies
    phases = config.get('phases', {})
    for phase_id, phase_config in phases.items():
        phase_name = f"Phase {phase_id}"
        depends_on = phase_config.get('depends_on', [])
        
        for dep_id in depends_on:
            dep_name = f"Phase {dep_id}"
            graph.add_dependency(phase_name, dep_name)
    
    # Add component dependencies
    components = config.get('components', {})
    for comp_name, comp_config in components.items():
        depends_on = comp_config.get('depends_on', [])
        
        for dep_comp in depends_on:
            graph.add_dependency(comp_name, dep_comp)
    
    return graph
