import importlib
import sys
from machine_learning.actions.base import BaseMLAction
from machine_learning.core.dtos import CollectionConfigDTO

PIPELINE_MAP = {
    'yu_broken_bottom': (
        'machine_learning.features.yu_broken_bottom_pipeline',
        'YuBrokenBottomPipeline',
    ),
}

class CollectAction(BaseMLAction):
    def execute(self, args, manager=None):
        config = CollectionConfigDTO(
            strategy=args.strategy,
            epics=args.epics,
            resolutions=args.resolutions,
            overwrite=args.overwrite
        )
        
        pipeline = self._load_pipeline(config.strategy)
        
        print(f"[INFO] Running data collection for {config.strategy}...")
        pipeline.run(
            epic=config.epics, 
            resolution=config.resolutions, 
            overwrite=config.overwrite
        )
        print("\n[SUCCESS] Data collection complete.")
        print(f"Next step: python machine_learning/train_model.py --strategy {config.strategy}")

    def _load_pipeline(self, strategy_key: str):
        if strategy_key not in PIPELINE_MAP:
            print(f"Error: No pipeline for '{strategy_key}'. Available: {list(PIPELINE_MAP.keys())}")
            sys.exit(1)
            
        module_path, class_name = PIPELINE_MAP[strategy_key]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)()
