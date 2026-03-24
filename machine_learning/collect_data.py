import argparse
import os
import sys

# Ensure project root is in sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from machine_learning.actions.collect_action import CollectAction

def main():
    parser = argparse.ArgumentParser(description='Collect ML features from backtest results.')
    parser.add_argument('--strategy', required=True, help='Strategy key (e.g. yu_broken_bottom)')
    parser.add_argument('--epics', required=False, help='Filtered asset (optional)')
    parser.add_argument('--resolutions', required=False, help='Filtered resolution (optional)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing dataset')
    
    args = parser.parse_args()
    
    action = CollectAction()
    action.execute(args)

if __name__ == '__main__':
    main()
