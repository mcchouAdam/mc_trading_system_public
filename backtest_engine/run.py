import sys
import os
import argparse
import pandas as pd
import numpy as np
import warnings

# Suppress annoying warnings from dependencies
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# Suppress FutureWarning for silently downcasting object dtype arrays
pd.set_option('future.no_silent_downcasting', True)

# Add parent and local path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.dirname(current_dir))

from core.engine import BacktestEngine
from actions.backtest_action import BacktestAction
from actions.optimize_action import OptimizeAction
from actions.wfo_action import WfoAction
from actions.audit_action import AuditAction

# Phase 1: Import C++ Strategies
CPP_CORE_PATH = os.path.join(os.path.dirname(current_dir), 
                             "trading_engine", "build", "core_lib_build", "Debug")
sys.path.append(CPP_CORE_PATH)

try:
    import mc_strategies
    print("[INFO] Successfully loaded C++ Trading Core (mc_strategies)")
except ImportError as e:
    print(f"[ERROR] Could not load C++ Trading Core from {CPP_CORE_PATH}: {e}")
    sys.exit(1)

def parse_dynamic_params(param_str):
    params = {}
    if not param_str: return params
    # Only parse the first group if multiple (for internal helper compatibility)
    # run.py main will handle the full splitting logic.
    main_group = param_str.split(';')[0]
    for pair in main_group.split(','):
        if '=' in pair:
            try:
                k, v = pair.split('=', 1)
                k = k.strip()
                v = v.strip()
                params[k] = float(v) if '.' in v else int(v)
            except ValueError:
                params[k] = v
    return params

def main():
    parser = argparse.ArgumentParser(description='MC Trading System - Unified Backtester')
    parser.add_argument('--mode', type=str, default='backtest', choices=['backtest', 'optimize', 'wfo', 'audit'])
    parser.add_argument('--strategy', type=str, default='PineL4', help='Strategy names (comma separated)')
    parser.add_argument('--epics', type=str, default='BTCUSD', help='Assets (comma separated)')
    parser.add_argument('--resolutions', type=str, default='DAY', help='Resolutions (comma separated)')
    parser.add_argument('--cash', type=float, default=10000)
    parser.add_argument('--fee', type=float, default=0.001)
    parser.add_argument('--params', type=str, default='', help='KEY=VAL,KEY2=VAL2 or S1:K=V;S2:K=V')
    parser.add_argument('--from', dest='from_date', type=str, help='YYYY-MM-DD')
    parser.add_argument('--to', dest='to_date', type=str, help='YYYY-MM-DD')
    parser.add_argument('--timezone', type=str, default='Asia/Taipei', help='Target timezone for reporting (e.g., Asia/Taipei, UTC)')
    parser.add_argument('--sizing-type', type=str, default='FIXED', choices=['FIXED', 'RISK'], help='Position sizing mode')
    parser.add_argument('--position-size', type=float, default=1.0, help='Units for FIXED, Percent for RISK')
    
    # Mode specific args
    parser.add_argument('--opt', type=str, help='KEY=START:END:STEP for optimization')
    parser.add_argument('--monte', action='store_true', help='Run Monte Carlo')
    parser.add_argument('--monte-n', type=int, default=1000)
    parser.add_argument('--ruin-pct', type=float, default=20.0)
    parser.add_argument('--use-ml', action='store_true')
    parser.add_argument('--wfo-splits', type=int, default=5)
    parser.add_argument('--wfo-train-ratio', type=float, default=0.7)
    parser.add_argument('--skip-sync', action='store_true', help='Skip syncing costs from Capital.com API')

    args = parser.parse_args()

    # 1. Initialize Strategies from C++
    strategies = []
    strategy_names = [s.strip() for s in args.strategy.split(',')]
    
    # Advanced Multi-Strategy Parsing
    groups = [g.strip() for g in args.params.split(';') if g.strip()]
    named_params = {}
    positional_params = []
    for g in groups:
        if ':' in g and '=' in g and g.find(':') < g.find('='):
            s_name, p_str = g.split(':', 1)
            named_params[s_name.strip()] = parse_dynamic_params(p_str)
        else:
            positional_params.append(parse_dynamic_params(g))

    for i, name in enumerate(strategy_names):
        if hasattr(mc_strategies, name):
            strategy_class = getattr(mc_strategies, name)
            
            # Param Selection Logic:
            # 1. Exact Name match ("YuBrokenBottom:...")
            # 2. Positional match (index based)
            # 3. Fallback to first group provided
            # 4. Empty dict
            p_dict = {}
            if name in named_params:
                p_dict = named_params[name]
            elif i < len(positional_params):
                p_dict = positional_params[i]
            elif positional_params:
                p_dict = positional_params[0]
                
            strategies.append(strategy_class(p_dict))
            print(f"[INFO] Initialized {name} with params: {p_dict}")
        else:
            print(f"[ERROR] Strategy {name} not found in C++ core.")
            sys.exit(1)

    # 2. Setup Engine
    engine = BacktestEngine(strategies, initial_cash=args.cash, fee=args.fee)
    # Inject helper into engine instance for actions to use
    engine.parse_params = parse_dynamic_params 

    # 3. Registry of Actions (Command Pattern)
    ACTIONS = {
        'backtest': BacktestAction(),
        'optimize': OptimizeAction(),
        'wfo': WfoAction(),
        'audit': AuditAction()
    }

    if args.mode in ACTIONS:
        ACTIONS[args.mode].execute(args, engine)
    else:
        print(f"[ERROR] Unknown mode: {args.mode}")

if __name__ == "__main__":
    main()
