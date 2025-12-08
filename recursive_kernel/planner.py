import yaml
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class Task:
    id: str
    domain: str
    type: str
    status: str
    description: str

class Planner:
    def __init__(self, config_path: str, backlog_path: str):
        self.config = self._load_yaml(config_path)
        self.backlog_path = backlog_path
        self.backlog = self._load_yaml(backlog_path)
    
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found")
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}

    def plan_next_task(self) -> Optional[Task]:
        safe_domains = self.config.get('safe_domains', [])
        tasks = self.backlog.get('tasks', [])
        
        if not tasks:
            return None

        for t in tasks:
            if t.get('status') == 'todo' and t.get('domain') in safe_domains:
                return Task(**t)
        return None
