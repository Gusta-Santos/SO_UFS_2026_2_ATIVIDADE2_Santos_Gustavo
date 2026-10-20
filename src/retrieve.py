"""Recuperacao: similaridade de cosseno por varredura (forca bruta) + montagem do contexto."""
import sqlite3, threading
import numpy as np
import vecstore


class Retriever:
    def __init__(self, index_dir, vec_mode="mmap"):
        self.db_path = vecstore.paths(index_dir)[0]
        self.mat = vecstore.open_vectors(index_dir, vec_mode)
        self.n = self.mat.shape[0]
        self._local = threading.local()             # uma conexao SQLite por thread

    def _con(self):
        c = getattr(self._local, "con", None)
        if c is None:
            c = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            self._local.con = c
        return c

    def search(self, query, k=5, max_ctx=2000):
        """Retorna (lista_de_trechos, bytes_do_contexto)."""
        q = vecstore.embed(query)
        if q is None:
            return [], 0
        scores = np.asarray(self.mat @ q)           # le o indice inteiro (RAM ou paginas do mmap)
        k = min(k, self.n)
        top = np.argpartition(-scores, k - 1)[:k]
        ids = [int(i) for i in top[np.argsort(-scores[top])]]
        marks = ",".join("?" * len(ids))
        rows = dict(self._con().execute(
            f"SELECT id, text FROM chunks WHERE id IN ({marks})", ids).fetchall())
        ctx, used = [], 0
        for i in ids:                               # contexto limitado a max_ctx bytes
            t = rows[i][:max_ctx - used]
            if not t:
                break
            ctx.append(t)
            used += len(t)
            if used >= max_ctx:
                break
        return ctx, used