"""
base_pipeline.py — Abstract base class for ML feature extraction pipelines.

Each strategy implements a subclass that knows:
  1. How to pre-compute vectorized features on OHLCV data
  2. How to extract a feature dict per individual trade
  3. (Optionally) how to override the default binary win/loss label

The base class handles everything else:
  - Loading trade records from the backtest reports
  - Loading OHLCV market data
  - Orchestrating the per-trade loop
  - Saving labelled records to machine_learning/datasets/{strategy_key}/labelled_dataset.jsonl
"""
import os
import json
import pandas as pd
import glob
from abc import ABC, abstractmethod
from machine_learning.core.dtos import MLSampleDTO

# Project root is the parent of the machine_learning/ folder
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class BasePipeline(ABC):
    """
    Abstract pipeline: backtest trades + OHLCV → labelled ML dataset.
    """

    strategy_name: str = None   # e.g. 'YuBrokenBottom'
    strategy_key:  str = None   # e.g. 'yu_broken_bottom'

    @abstractmethod
    def prepare_market_data(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def extract_features(self, feat_df: pd.DataFrame, trade: pd.Series) -> dict:
        pass

    def get_label(self, trade: pd.Series) -> int:
        return 1 if float(trade['pnl']) > 0 else 0

    def _load_trades(self, epic: str = None, resolution: str = None) -> pd.DataFrame:
        """
        Loads trade records from the machine_learning/to_be_labelled_data directory.
        Supports loading and merging multiple files based on filters.
        """
        assert self.strategy_name, "Subclass must set strategy_name"
        source_dir = os.path.join(_PROJECT_ROOT, 'machine_learning', 'to_be_labelled_data')
        os.makedirs(source_dir, exist_ok=True)
        
        # Look for all matching CSVs
        pattern = os.path.join(source_dir, f"Trades_*{self.strategy_name}*.csv")
        all_files = glob.glob(pattern)
        
        if not all_files:
            raise FileNotFoundError(f"No trade logs found in {source_dir} for strategy {self.strategy_name}")

        filtered_files = []
        for f in all_files:
            basename = os.path.basename(f)
            # Filter by Epic string if provided
            if epic and epic not in basename:
                continue
            # Filter by Resolution (exact match with underscores to avoid MINUTE vs MINUTE_15)
            if resolution:
                res_part = f"_{resolution}_"
                if res_part not in basename:
                     continue
            filtered_files.append(f)

        if not filtered_files:
            print(f"  [WARN] No files matched filters (Epic: {epic}, Res: {resolution}) in {source_dir}")
            return pd.DataFrame()

        # Load and merge all matched files
        dfs = []
        for f in filtered_files:
            print(f"  [Merge] Loading trades from: {os.path.basename(f)}")
            df_item = pd.read_csv(f)
            dfs.append(df_item)
            
        df = pd.concat(dfs, ignore_index=True)
        df['entry_time'] = pd.to_datetime(df['entry_time'], format='mixed')
        df['exit_time']  = pd.to_datetime(df['exit_time'], format='mixed')

        # Final safety filter by strategy name prefix
        filtered = df[df['strategy'].str.startswith(self.strategy_name)].copy()
        
        if filtered.empty:
            print(f"  [WARN] Strategy filter '{self.strategy_name}' yielded 0 rows after merge.")
            
        return filtered

    def _load_market_data(self, epic: str, resolution: str) -> pd.DataFrame:
        """Load data from database (using engine logic) or parquet if available."""
        # For pipeline, we can use a temporary simplified DB loader or rely on BacktestEngine
        from backtest_engine.core.engine import BacktestEngine
        engine = BacktestEngine(strategies=[])
        df = engine.load_data(epic, resolution)
        if df is None:
            raise FileNotFoundError(f"Market data not found for {epic} {resolution}")
        return df

    def _output_path(self) -> str:
        assert self.strategy_key, "Subclass must set strategy_key"
        dataset_dir = os.path.join(_PROJECT_ROOT, 'machine_learning', 'datasets', self.strategy_key)
        os.makedirs(dataset_dir, exist_ok=True)
        return os.path.join(dataset_dir, 'labelled_dataset.jsonl')

    def run(self, epic: str = None, resolution: str = None, overwrite: bool = False) -> str:
        print(f"\n{'='*60}")
        print(f"Feature Pipeline: {self.strategy_name} | Merge Mode")
        print(f"Filters -> Epic: {epic}, Res: {resolution}")
        print(f"{'='*60}")

        trades_df = self._load_trades(epic, resolution)
        if trades_df.empty:
            print("[ERROR] No trades to process. Exiting.")
            return ""

        # For market data loading, we need to know WHICH epic/res to load.
        # If multiple were merged, we might need a more complex loop, 
        # but for now we'll support the provided epic/res if given, 
        # otherwise we'll try to infer from the data (though inferring is tricky).
        
        # Heuristic: if epic/res not provided, process first row's epic/res 
        # (This is a limitation of current single-epic run_backtest logic)
        load_epic = epic or trades_df.iloc[0]['strategy'].split('_')[1]
        load_res  = resolution or trades_df.iloc[0]['strategy'].split('_')[2]

        market_df = self._load_market_data(load_epic, load_res)

        print(f"  Pre-computing features on {len(market_df)} bars...")
        feat_df = self.prepare_market_data(market_df)

        output_path = self._output_path()
        mode = 'w' if overwrite else 'a'
        labelled, skipped = 0, 0

        with open(output_path, mode) as f:
            for _, trade in trades_df.iterrows():
                entry_time = trade['entry_time']
                
                # Align entry_time timezone with feat_df if necessary
                if entry_time.tzinfo is None and feat_df.index.tz is not None:
                    entry_time = entry_time.tz_localize('UTC').tz_convert(feat_df.index.tz)
                elif entry_time.tzinfo is not None and feat_df.index.tz is not None:
                    entry_time = entry_time.tz_convert(feat_df.index.tz)
                
                # Find the closest matching bar in feat_df (allowing small tolerance for timezone/alignment)
                try:
                    # Direct match
                    if entry_time not in feat_df.index:
                        # Try finding the closest bar before entry_time
                        idx = feat_df.index.get_indexer([entry_time], method='pad')[0]
                        if idx == -1:
                            skipped += 1
                            continue
                        entry_time = feat_df.index[idx]
                    
                    # Update trade entry_time to the aligned one for extract_features
                    trade = trade.copy()
                    trade['entry_time'] = entry_time
                    
                    features = self.extract_features(feat_df, trade)
                    label = self.get_label(trade)
                    record = MLSampleDTO(
                        trade_id=f"{self.strategy_key}_{entry_time.strftime('%Y%m%d_%H%M')}",
                        timestamp=entry_time.isoformat(),
                        epic=load_epic,
                        resolution=load_res,
                        features=features,
                        outcome=label,
                        pnl_ratio=float(trade['pnl'])
                    )
                    f.write(json.dumps(record.to_dict()) + '\n')
                    labelled += 1
                except Exception as e:
                    skipped += 1
                    continue

        print(f"  Output:    {output_path}")
        print(f"  Labelled:  {labelled} | Skipped: {skipped}")
        return output_path
