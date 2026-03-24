import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

ENV = os.getenv("ENVIRONMENT", "local")
print(f"Loaded configuration for {ENV} environment from .env")

class Config:
    @staticmethod
    def get(key: str, default: str = None) -> str:
        val = os.getenv(key)
        
        if val:
            return val
                
        return default
