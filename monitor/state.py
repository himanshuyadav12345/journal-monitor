import json
from pathlib import Path

def load_seen(path):
    p=Path(path)
    if not p.exists(): return set()
    try: return set(json.loads(p.read_text(encoding="utf-8")))
    except Exception: return set()

def save_seen(path, seen):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(sorted(seen),ensure_ascii=False,indent=2),encoding="utf-8")
