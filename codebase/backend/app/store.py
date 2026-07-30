import json
from copy import deepcopy
from pathlib import Path
from threading import RLock

from .seed import initial_state


class JsonStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = RLock()
        self._state: dict = {}
        self._load_or_seed()

    def _load_or_seed(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self._state = json.loads(self.path.read_text(encoding="utf-8"))
                required = {
                    "discord_messages",
                    "memories",
                    "candidates",
                    "assistant_messages",
                    "ingestion",
                }
                if required.issubset(self._state):
                    return
            except (json.JSONDecodeError, OSError):
                pass
        self._state = initial_state()
        self._persist()

    def _persist(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def snapshot(self) -> dict:
        with self._lock:
            return deepcopy(self._state)

    def mutate(self, operation):
        with self._lock:
            result = operation(self._state)
            self._persist()
            return deepcopy(result)

    def reset(self) -> dict:
        with self._lock:
            self._state = initial_state()
            self._persist()
            return deepcopy(self._state)
