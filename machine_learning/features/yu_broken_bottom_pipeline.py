import pandas as pd
import numpy as np
from machine_learning.features.base_pipeline import BasePipeline
from machine_learning.core.dtos import YuBrokenBottomFeaturesDTO

class YuBrokenBottomPipeline(BasePipeline):
    strategy_name = 'YuBrokenBottom'
    strategy_key  = 'yu_broken_bottom'

    def prepare_market_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorized feature calculation."""
        # 1. Volatility
        df['feat_atr'] = self._calculate_atr(df, 14)
        df['feat_volatility'] = df['close'].pct_change().rolling(20).std()
        
        # 2. RSI
        df['feat_rsi'] = self._calculate_rsi(df, 14)
        
        # 3. Distance from EMA
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['feat_dist_ema20'] = (df['close'] - df['ema_20']) / df['ema_20']
        
        # 4. Volume Trend
        df['feat_vol_ma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        return df.fillna(0)

    def extract_features(self, feat_df: pd.DataFrame, trade: pd.Series) -> dict:
        """Extract features at entry_time."""
        entry_time = trade['entry_time']
        # If entry_time is not exactly in index (due to sub-bar entry), 
        # BasePipeline should have handled padding, but we'll be safe
        if entry_time not in feat_df.index:
            entry_time = feat_df.index[feat_df.index.get_indexer([entry_time], method='pad')[0]]
            
        row = feat_df.loc[entry_time]
        
        features = YuBrokenBottomFeaturesDTO(
            rsi=float(row['feat_rsi']),
            volatility=float(row['feat_volatility']),
            dist_ema20=float(row['feat_dist_ema20']),
            vol_ratio=float(row['feat_vol_ma_ratio']),
            atr_norm=float(row['feat_atr'] / row['close'])
        )
        return features.to_dict()

    def _calculate_atr(self, df, window=14):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=window).mean()

    def _calculate_rsi(self, df, window=14):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1+rs))
