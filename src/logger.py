"""Log de eventos com escrita concorrente protegida por lock."""
import json, os, threading, time
from contextlib import nullcontext


class EventLog:
    def __init__(self, path, locked=True):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.f = open(path, "w", encoding="utf-8")
        # locked=False existe so para a demonstracao de log intercalado (Parte D)
        self._lock = threading.Lock() if locked else nullcontext()

    def log(self, event, **kv):
        line = (f"{time.time():.6f}\t{threading.current_thread().name}\t{event}\t"
                + json.dumps(kv, ensure_ascii=False) + "\n")
        with self._lock:
            self.f.write(line)

    def close(self):
        with self._lock:
            self.f.flush()
            self.f.close()