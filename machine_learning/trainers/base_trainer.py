"""
base_trainer.py — Abstract Base Trainer for all ML filter models.

Each strategy that wants ML filtering implements a subclass here.
The base handles: model training, evaluation, versioned saving, and registry registration.
"""
import os
import sys
import json
from abc import ABC, abstractmethod
from datetime import datetime
import joblib
import pandas as pd
from machine_learning.core.registry import ModelRegistryManager
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _PROJECT_ROOT)


class BaseTrainer(ABC):
    """
    Abstract base class for all strategy ML trainers.

    To add a new strategy's ML trainer:
      1. Create a subclass in machine_learning/trainers/
      2. Set `strategy_key` to match the key in model_registry.json
      3. Implement `load_dataset()` and `prepare_features()`
      4. Register the trainer in machine_learning/train_model.py's TRAINER_MAP

    The `train()` method handles: training, evaluation, saving, and registry registration.
    """

    # Must match the key used in model_registry.json
    strategy_key: str = None

    @abstractmethod
    def load_dataset(self) -> pd.DataFrame:
        """
        Load and return the labelled dataset.
        Must include an 'outcome' column (1 = win, 0 = loss).
        """
        pass

    @abstractmethod
    def prepare_features(self, df: pd.DataFrame):
        """
        Prepare and return (X, y) for training.
        X: pd.DataFrame of features
        y: pd.Series of binary labels (1 = win, 0 = loss)
        """
        pass

    def get_model(self):
        """
        Return the sklearn model to train. Override to change model type.
        Default: Random Forest with sensible defaults.
        """
        return RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)

    def train(self, notes: str = "") -> str:
        """
        Full training pipeline:
          1. Load dataset
          2. Prepare features
          3. Train + evaluate model
          4. Save versioned model file
          5. Register in model_registry.json as 'candidate'

        Returns: version tag (e.g. 'v2')
        """
        manager = ModelRegistryManager()

        assert self.strategy_key, "Subclass must set strategy_key"

        print(f"\n{'='*60}")
        print(f"Training ML filter: {self.strategy_key}")
        print(f"{'='*60}")

        # 1. Load data
        print("Loading dataset...")
        df = self.load_dataset()
        print(f"  Loaded {len(df)} samples")

        # 2. Prepare features
        X, y = self.prepare_features(df)
        
        # REQUIRED: Sort feature names alphabetically once to standardize all future runs
        X = X.reindex(sorted(X.columns), axis=1)
        
        print(f"  Features ({X.shape[1]}): {list(X.columns)}")
        print(f"  Win rate: {y.mean():.2%}  ({int(y.sum())} wins / {len(y)} total)")

        # 3. Split (time-aware: no shuffle for temporal data)
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        print(f"  Train: {len(X_train)}  |  Test: {len(X_test)}")

        # 4. Train
        print("\nTraining model...")
        model = self.get_model()
        model.fit(X_train, y_train)

        # 5. Evaluate
        y_pred  = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, y_pred)

        print(f"\nTest Accuracy: {acc:.2%}")
        print(classification_report(y_test, y_pred, zero_division=0))

        # 6. Feature importance
        if hasattr(model, 'feature_importances_'):
            imp = sorted(zip(X.columns, model.feature_importances_), key=lambda x: -x[1])
            print("Feature Importance:")
            for name, val in imp:
                bar = '█' * int(val * 40)
                print(f"  {name:30} {val:.4f} {bar}")

        # 7. High-confidence trade analysis (threshold 0.6)
        high_conf = y_proba >= 0.6
        if high_conf.any():
            orig_wr = float(y_test.mean())
            hc_wr   = float(y_test[high_conf].mean())
            print(f"\nHigh-confidence (>=60%) - Win rate: {orig_wr:.2%} -> {hc_wr:.2%} "
                  f"({high_conf.sum()} of {len(y_test)} trades kept)")

        # 8. Save versioned model
        models_dir = os.path.join(_PROJECT_ROOT, 'machine_learning', 'models')
        os.makedirs(models_dir, exist_ok=True)
        datestamp    = datetime.now().strftime('%Y%m%d')
        filename     = f"{self.strategy_key}_{datestamp}.joblib"
        abs_path     = os.path.join(models_dir, filename)
        rel_path     = f"machine_learning/models/{filename}"
        joblib.dump(model, abs_path)
        print(f"\nModel saved: {abs_path}")

        # 9. Register as candidate
        if not notes:
            notes = (f"RF n_estimators=100, max_depth=5. "
                     f"Test acc={acc:.2%}, baseline win rate={y.mean():.2%}")
        version_tag = manager.register_version(self.strategy_key, rel_path, notes)

        print(f"\nNext step — validate, then promote:")
        print(f"  python machine_learning/promote_model.py promote "
              f"--strategy {self.strategy_key} --version {version_tag}")

        return version_tag
