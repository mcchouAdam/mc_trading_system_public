from machine_learning.actions.base import BaseMLAction
from datetime import datetime

class PromoteAction(BaseMLAction):
    def execute(self, args, manager):
        command_map = {
            "promote": lambda: self._promote(args.strategy, args.version, manager),
            "list": lambda: self._list_versions(args.strategy, manager)
        }
        
        handler = command_map.get(args.command)
        if handler:
            handler()
        else:
            print(f"[ERROR] Unknown command: {args.command}")

    def _promote(self, strategy_name: str, version: str, manager):
        try:
            success = manager.promote_version(strategy_name, version)
            if success:
                strategy = manager.get_strategy(strategy_name)
                print("=" * 60)
                print(f"  PROMOTED: {strategy_name} → {version}")
                print(f"  Model:    {strategy.production}")
                print(f"  Date:     {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                print("=" * 60)
                print("  Trading engine will use the new model on next restart.")
            else:
                print(f"'{version}' is already the production model. No changes made.")
        except Exception as e:
            print(f"[ERROR] Promotion failed: {e}")

    def _list_versions(self, strategy_name: str, manager):
        registry = manager.load_all()
        strategies = [strategy_name] if strategy_name else [k for k in registry.keys() if not k.startswith("_")]

        for s in strategies:
            if s not in registry:
                print(f"Strategy '{s}' not found.")
                continue
            
            entry = registry[s]
            print(f"\n{s}:")
            print(f"  Production: {entry.production or 'none'}")
            for v in entry.versions:
                marker = "← PRODUCTION" if v.path == entry.production else ""
                print(f"  [{v.status:8}] {v.version:6} | {v.path} {marker}")
