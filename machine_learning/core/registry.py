import json
import os
from datetime import datetime
from typing import Dict, Optional, List
from machine_learning.core.dtos import StrategyRegistryDTO, ModelVersionDTO

class ModelRegistryManager:
    """Manages reading, writing, and updating model_registry.json."""
    
    def __init__(self, registry_path: Optional[str] = None):
        if registry_path is None:
            registry_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model_registry.json")
        self.registry_path = registry_path

    def load_all(self) -> Dict[str, Any]:
        if not os.path.exists(self.registry_path):
            return {}
            
        with open(self.registry_path, "r") as f:
            data = json.load(f)
            
        registry = {}
        for key, content in data.items():
            if key.startswith("_"):
                registry[key] = content
                continue
            
            version_dicts = content.get("versions", [])
            versions = []
            for v in version_dicts:
                valid_keys = ModelVersionDTO.__dataclass_fields__.keys()
                filtered_v = {k: val for k, val in v.items() if k in valid_keys}
                versions.append(ModelVersionDTO(**filtered_v))
            
            registry[key] = StrategyRegistryDTO(
                strategy_name=key,
                versions=versions,
                production=content.get("production"),
                enabled=content.get("enabled", True),
                threshold=content.get("threshold", 0.5)
            )
        return registry

    def save_all(self, registry: Dict[str, Any]):
        data = {}
        for key, val in registry.items():
            if key.startswith("_"):
                data[key] = val
            else:
                data[key] = val.to_dict()
                
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_strategy(self, strategy_name: str) -> Optional[StrategyRegistryDTO]:
        registry = self.load_all()
        return registry.get(strategy_name)

    def register_version(self, strategy_name: str, model_path: str, notes: str = "") -> str:
        registry = self.load_all()
        
        if strategy_name not in registry:
            registry[strategy_name] = StrategyRegistryDTO(strategy_name=strategy_name)
            
        strategy_entry = registry[strategy_name]
        
        # Auto-increment version number
        existing_nums = []
        for v in strategy_entry.versions:
            ver = v.version
            if ver.startswith("v") and ver[1:].isdigit():
                existing_nums.append(int(ver[1:]))
        next_num = max(existing_nums, default=0) + 1
        version_tag = f"v{next_num}"

        new_version = ModelVersionDTO(
            version=version_tag,
            path=model_path,
            trained_date=datetime.now().strftime("%Y-%m-%d"),
            status="candidate",
            notes=notes
        )
        strategy_entry.versions.append(new_version)
        self.save_all(registry)
        return version_tag

    def promote_version(self, strategy_name: str, version: str) -> bool:
        registry = self.load_all()
        if strategy_name not in registry:
            raise ValueError(f"Strategy '{strategy_name}' not found in registry.")

        entry = registry[strategy_name]
        target = next((v for v in entry.versions if v.version == version), None)
        if not target:
            raise ValueError(f"Version '{version}' not found for strategy '{strategy_name}'.")

        # Validate file existence
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        abs_path = os.path.join(project_root, target.path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Model file not found: {abs_path}")

        if entry.production == target.path:
            return False # Already production

        # Demote old production
        for v in entry.versions:
            if v.path == entry.production and v.status == "production":
                v.status = "archived"
                v.demoted_date = datetime.now().strftime("%Y-%m-%d")

        # Promote new
        target.status = "production"
        target.promoted_date = datetime.now().strftime("%Y-%m-%d")
        entry.production = target.path

        self.save_all(registry)
        return True
