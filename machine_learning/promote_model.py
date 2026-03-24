import argparse
import os
import sys

# Ensure project root is in sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from machine_learning.core.registry import ModelRegistryManager
from machine_learning.actions.promote_action import PromoteAction

def main():
    parser = argparse.ArgumentParser(description="ML Model Promotion Tool")
    sub = parser.add_subparsers(dest="command")

    # promote command
    p_promote = sub.add_parser("promote", help="Promote a version to production")
    p_promote.add_argument("--strategy", required=True)
    p_promote.add_argument("--version",  required=True)

    # list command
    p_list = sub.add_parser("list", help="List all versions")
    p_list.add_argument("--strategy", default=None)

    args = parser.parse_args()
    
    manager = ModelRegistryManager()
    action = PromoteAction()
    action.execute(args, manager)

if __name__ == '__main__':
    main()
