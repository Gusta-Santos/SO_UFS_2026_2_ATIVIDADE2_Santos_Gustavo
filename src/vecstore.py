"""Vetores simulados e acesso ao indice em disco (SQLite + arquivo binario float32)."""
import json
import os
import numpy as np

DIM = 128
VOCAB = 5000          # mesmo vocabulario do gerador de corpus (termo0..termo4999)
SEED = 7
VOCAB_IDS = {f"termo{i}": i for i in range(VOCAB)}
_TABLE = None


def table():
    """Tabela fixa (VOCAB x DIM) de vetores aleatorios, um por termo."""
    global _TABLE
    if _TABLE is None:
        _TABLE = np.random.default_rng(SEED).standard_normal((VOCAB, DIM)).astype(np.float32)
    return _TABLE


def embed(text):
    """Vetor simulado: media dos vetores dos termos, normalizada. Textos com termos
    em comum ficam proximos, entao a recuperacao e coerente."""
    ids = [VOCAB_IDS[t] for t in text.split() if t in VOCAB_IDS]
    if not ids:
        return None
    v = table()[ids].mean(axis=0)
    n = float(np.linalg.norm(v))
    return (v / n).astype(np.float32) if n > 0 else None


def paths(index_dir):
    return (os.path.join(index_dir, "chunks.db"),
            os.path.join(index_dir, "vectors.f32"),
            os.path.join(index_dir, "meta.json"))


def load_meta(index_dir):
    with open(paths(index_dir)[2]) as f:
        return json.load(f)


def open_vectors(index_dir, mode="mmap"):
    """mode='mmap': np.memmap (paginas sob demanda). mode='ram': carrega tudo na RAM."""
    vec = paths(index_dir)[1]
    n = load_meta(index_dir)["n_chunks"]
    if mode == "mmap":
        return np.memmap(vec, dtype=np.float32, mode="r", shape=(n, DIM))
    return np.fromfile(vec, dtype=np.float32).reshape(n, DIM)


def size_mb(path):
    return os.path.getsize(path) / 1048576