"""Load optional, Git-ignored local AI settings without evaluating file contents."""
import os
from pathlib import Path

AI_SETTINGS = {'NVIDIA_API_KEY', 'NVIDIA_MODEL'}


def load_local_env(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name('.env')
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, separator, value = line.partition('=')
        name, value = name.strip(), value.strip()
        if separator and name in AI_SETTINGS:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            os.environ.setdefault(name, value)
