import json
import os
from datetime import datetime
from typing import Dict, List

class MetricsLogger:
    """Handles persistent logging of test metrics and historical snapshots"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.current_log_file = os.path.join(log_dir, f"execution_{datetime.now().strftime('%Y%p%d_%H%M%S')}.json")

    def log_snapshot(self, summary: Dict, components: Dict):
        """Save a complete snapshot of the current execution state"""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "components": {name: self._serialize_comp(c) for name, c in components.items()}
        }
        
        # Append to individual execution log
        with open(self.current_log_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
            
        # Also append to history master log
        history_file = os.path.join(self.log_dir, "history.jsonl")
        with open(history_file, 'a') as f:
            f.write(json.dumps(snapshot) + "\n")

    def _serialize_comp(self, comp) -> Dict:
        return {
            "name": comp.name,
            "passed": comp.passed,
            "failed": comp.failed,
            "errors": comp.errors,
            "skipped": comp.skipped,
            "coverage": comp.coverage,
            "duration": comp.duration,
            "pass_rate": comp.pass_rate
        }

    def get_history(self) -> List[Dict]:
        """Retrieve historical execution snapshots"""
        history_file = os.path.join(self.log_dir, "history.jsonl")
        if not os.path.exists(history_file):
            return []
            
        history = []
        with open(history_file, 'r') as f:
            for line in f:
                if line.strip():
                    history.append(json.loads(line))
        return history
