import json
import os

STATE_FILE = "state.json"

def load():
    if not os.path.exists(STATE_FILE):
        return {"last_update_id": 0, "processed": []}
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
