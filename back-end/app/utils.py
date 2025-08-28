import os
from pathlib import Path

def get_env_var(name: str, default=None):
    return os.getenv(name, default)

def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
