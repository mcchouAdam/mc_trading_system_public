"""
yu_broken_bottom_trainer.py — ML trainer for the YuBrokenBottom strategy.

Dataset: backtest_engine/machine_learning/yu_ml_dataset.jsonl
Features: same as extract_ml_features() in the strategy class
"""
import json
import os
import sys
import pandas as pd

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _PROJECT_ROOT)

from machine_learning.trainers.base_trainer import BaseTrainer


class YuBrokenBottomTrainer(BaseTrainer):
    strategy_key = 'yu_broken_bottom'

    def load_dataset(self) -> pd.DataFrame:
        path = os.path.join(
            _PROJECT_ROOT, 'machine_learning', 'datasets', self.strategy_key, 'labelled_dataset.jsonl'
        )
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Dataset not found at {path}.\nRun data collection first:\n"
                f"  python machine_learning/collect_data.py --strategy {self.strategy_key} ..."
            )
        print(f"  Loading dataset from: {path}")
        rows = []
        with open(path) as f:
            for line in f:
                entry = json.loads(line)
                row = entry['features']
                row['outcome'] = entry['outcome']
                rows.append(row)
        return pd.DataFrame(rows)

    def prepare_features(self, df: pd.DataFrame):
        # Drop columns that are either labels or too close to the label
        drop_cols = ['outcome', 'pnl_ratio']
        X = df.drop([c for c in drop_cols if c in df.columns], axis=1)
        y = df['outcome'].astype(int)
        return X, y
