from abc import ABC, abstractmethod

class BaseMLAction(ABC):
    @abstractmethod
    def execute(self, args, manager=None):
        pass
