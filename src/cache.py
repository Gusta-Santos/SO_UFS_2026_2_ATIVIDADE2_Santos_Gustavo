"""Cache compartilhado (LRU ou FIFO) com contadores e protecao por lock."""
import threading
from collections import OrderedDict
from contextlib import nullcontext


class SharedCache:
    def __init__(self, capacity=64, policy="lru", locked=True):
        self.cap, self.policy = capacity, policy
        self.d = OrderedDict()                      # chave -> (valor, custo_s)
        # locked=False existe so para a demonstracao de condicao de corrida (Parte D)
        self._lock = threading.Lock() if locked else nullcontext()
        self.hits = self.misses = self.evictions = 0
        self.saved_s = 0.0

    def get(self, key):
        with self._lock:
            if key in self.d:
                if self.policy == "lru":
                    self.d.move_to_end(key)
                val, cost = self.d[key]
                self.hits += 1
                self.saved_s += cost                # tempo que o calculo original custou
                return val
            self.misses += 1
            return None

    def put(self, key, val, cost_s):
        if self.cap <= 0:
            return
        with self._lock:
            if key in self.d:
                self.d[key] = (val, cost_s)
                if self.policy == "lru":
                    self.d.move_to_end(key)
                return
            if len(self.d) >= self.cap:
                self.d.popitem(last=False)          # remove o mais antigo (LRU ou FIFO)
                self.evictions += 1
            self.d[key] = (val, cost_s)

    def stats(self):
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses, "evictions": self.evictions,
                "hit_rate": round(self.hits / total, 4) if total else 0.0,
                "size": len(self.d), "saved_s": round(self.saved_s, 4)}