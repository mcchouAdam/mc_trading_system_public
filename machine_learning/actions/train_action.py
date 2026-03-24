import importlib
import sys
from machine_learning.actions.base import BaseMLAction
from machine_learning.core.dtos import TrainingConfigDTO

TRAINER_MAP = {
    'yu_broken_bottom': 'machine_learning.trainers.yu_broken_bottom_trainer.YuBrokenBottomTrainer',
}

class TrainAction(BaseMLAction):
    def execute(self, args, manager=None):
        config = TrainingConfigDTO(
            strategy=args.strategy,
            notes=args.notes
        )
        
        trainer = self._load_trainer(config.strategy)
        
        print(f"[INFO] Starting training for {config.strategy}...")
        # Note: The trainer internally uses ModelRegistryManager or similar 
        # to register itself. We should ensure it's consistent.
        trainer.train(notes=config.notes)
        
        print(f"\n[SUCCESS] Training complete for {config.strategy}.")
        print(f"Next step: python machine_learning/promote_model.py list --strategy {config.strategy}")

    def _load_trainer(self, strategy_key: str):
        if strategy_key not in TRAINER_MAP:
            print(f"Error: No trainer registered for '{strategy_key}'.")
            sys.exit(1)

        module_path, class_name = TRAINER_MAP[strategy_key].rsplit('.', 1)
        module = importlib.import_module(module_path)
        TrainerClass = getattr(module, class_name)
        return TrainerClass()
