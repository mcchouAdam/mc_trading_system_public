import os
import json
import joblib
import pandas as pd
import importlib

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class MLInferenceHandler:
    def __init__(self):
        self.registry_path = os.path.join(_PROJECT_ROOT, 'machine_learning', 'model_registry.json')
        self.registry = self._load_registry()
        self.pipelines = {}
        self.models = {}

    def _load_registry(self):
        if not os.path.exists(self.registry_path):
            return {}
        with open(self.registry_path, 'r') as f:
            return json.load(f)

    def get_production_model(self, strategy_key):
        """Load the production model for the given strategy."""
        if strategy_key not in self.registry:
            return None
            
        entry = self.registry[strategy_key]
        if not entry.get('enabled', False):
            return None
            
        model_path_rel = entry.get('production')
        if not model_path_rel:
            return None
            
        model_path = os.path.join(_PROJECT_ROOT, model_path_rel)
        
        if strategy_key not in self.models:
            if os.path.exists(model_path):
                print(f"[ML] Loading production model from {model_path}...")
                self.models[strategy_key] = joblib.load(model_path)
            else:
                print(f"[ML] Error: Model file not found at {model_path}")
                return None
        return self.models[strategy_key]

    def get_pipeline(self, strategy_key):
        """Dynamically load the feature pipeline."""
        if strategy_key in self.pipelines:
            return self.pipelines[strategy_key]

        # Map strategy key to pipeline class (should match collect_data.py)
        # In a real system, this mapping could also be in a config or the registry
        mapping = {
            'yu_broken_bottom': ('machine_learning.features.yu_broken_bottom_pipeline', 'YuBrokenBottomPipeline')
        }
        
        if strategy_key not in mapping:
            return None
            
        module_path, class_name = mapping[strategy_key]
        try:
            module = importlib.import_module(module_path)
            self.pipelines[strategy_key] = getattr(module, class_name)()
            return self.pipelines[strategy_key]
        except Exception:
            return None

    def apply_ml_filter(self, strategy_key, df, entries):
        """
        Filter entries using ML model.
        df: Full OHLCV DataFrame
        entries: Boolean Series of trade entries
        """
        model = self.get_production_model(strategy_key)
        pipeline = self.get_pipeline(strategy_key)
        
        if not model or not pipeline or not entries.any():
            return entries

        print(f"[ML] Applying filter for {strategy_key} using production model...")
        
        # 1. Pre-compute features
        feat_df = pipeline.prepare_market_data(df.copy())
        
        # 2. Extract features for each entry
        entry_indices = entries[entries].index
        
        feature_list = []
        for ts in entry_indices:
            # We pass a dummy trade series just to satisfy the API
            dummy_trade = pd.Series({'entry_time': ts})
            features = pipeline.extract_features(feat_df, dummy_trade)
            feature_list.append(features)
            
        # 3. Predict
        X = pd.DataFrame(feature_list)
        
        # REQUIRED: Ensure feature columns match the model's training order
        if hasattr(model, 'feature_names_in_'):
            # If the model has stored feature names, use them to re-order our new data
            X = X.reindex(columns=model.feature_names_in_)
        else:
            # Fallback to sorted order
            X = X.reindex(sorted(X.columns), axis=1)
        
        # Get threshold from registry or use 0.5 default
        threshold = self.registry[strategy_key].get('threshold', 0.5)
        probs = model.predict_proba(X)[:, 1]
        
        avg_prob = float(probs.mean())
        max_prob = float(probs.max())
        mask = probs >= threshold
        
        # Update entries: keep only those that passed ML filter
        new_entries = pd.Series(False, index=entries.index)
        new_entries.loc[entry_indices[mask]] = True
        
        filtered_count = len(entry_indices) - mask.sum()
        print(f"[ML] Filtered out {filtered_count} / {len(entry_indices)} trades.")
        print(f"[ML] Confidence Stats -> Avg: {avg_prob:.2f} | Max: {max_prob:.2f} | Threshold: {threshold:.2f}")
        
        return new_entries
