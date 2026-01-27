import json
from pathlib import Path
from typing import Any, Dict

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def _file_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"

def load(name: str) -> Dict[str, Any]:
    path = _file_path(name)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save(name: str, data: Dict[str, Any]) -> None:
    path = _file_path(name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
