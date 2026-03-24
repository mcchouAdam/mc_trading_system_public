import argparse
import sys
import os

# Ensure project root is in sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from machine_learning.actions.train_action import TrainAction

def main():
    parser = argparse.ArgumentParser(description='Train ML filter model for a strategy.')
    parser.add_argument('--strategy', required=True, help='Strategy key (must match model_registry.json entry)')
    parser.add_argument('--notes', default='', help='Description of this training run (stored in model_registry.json)')
    
    args = parser.parse_args()

    action = TrainAction()
    action.execute(args)

if __name__ == '__main__':
    main()
