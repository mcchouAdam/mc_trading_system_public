from abc import ABC, abstractmethod
import argparse

class BaseAction(ABC):
    @abstractmethod
    def execute(self, args: argparse.Namespace, engine):
        pass
