"""Ingestao: le o corpus, fragmenta em chunks, gera vetores simulados e grava o indice
(SQLite com os textos + arquivo binario com os vetores)."""
import argparse, csv, datetime, json, os, shutil, sqlite3, subprocess, time
import numpy as np
import store, vecstore


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--chunk-words", type=int, default=40)
    ap.add_argument("--batch", type=int, default=20000)
    ap.add_argument("--out", default="results/raw/ingest.csv")
    a = ap.parse_args()

    commit = git_commit()
    if os.path.exists(a.index_dir):
        shutil.rmtree(a.index_dir)
    os.makedirs(a.index_dir)
    db_path, vec_path, meta_path = vecstore.paths(a.index_dir)

    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, doc TEXT, pos INTEGER, text TEXT)")
    tbl, vid = vecstore.table(), vecstore.VOCAB_IDS
    s0 = store.snapshot()
    t0 = time.perf_counter()
    n_docs = n_chunks = 0
    rows, vecs = [], []

    def flush(vf):
        con.executemany("INSERT INTO chunks VALUES (?,?,?,?)", rows)
        con.commit()
        np.asarray(vecs, dtype=np.float32).tofile(vf)
        rows.clear(); vecs.clear()

    with open(a.corpus, encoding="utf-8") as f, open(vec_path, "wb") as vf:
        for line in f:
            head, _, body = line.strip().partition("] ")
            words = body.split()
            if not words:
                continue
            n_docs += 1
            for pos, i in enumerate(range(0, len(words), a.chunk_words)):
                w = words[i:i + a.chunk_words]
                ids = [vid[t] for t in w if t in vid]
                if not ids:
                    continue
                v = tbl[ids].mean(axis=0)
                v /= (float(np.linalg.norm(v)) or 1.0)
                rows.append((n_chunks, head.lstrip("["), pos, " ".join(w)))
                vecs.append(v)
                n_chunks += 1
                if len(rows) >= a.batch:
                    flush(vf)
        if rows:
            flush(vf)
        vf.flush(); os.fsync(vf.fileno())
    con.close()
    t1 = time.perf_counter()
    s1 = store.snapshot()

    with open(meta_path, "w") as f:
        json.dump({"n_chunks": n_chunks, "dim": vecstore.DIM, "chunk_words": a.chunk_words,
                   "corpus": os.path.basename(a.corpus), "n_docs": n_docs}, f)

    MB = 1048576
    row = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"), "commit": commit,
        "corpus": os.path.basename(a.corpus), "corpus_mb": round(vecstore.size_mb(a.corpus), 1),
        "n_docs": n_docs, "n_chunks": n_chunks, "chunk_words": a.chunk_words,
        "db_mb": round(vecstore.size_mb(db_path), 1), "vec_mb": round(vecstore.size_mb(vec_path), 1),
        "ingest_s": round(t1 - t0, 3),
        "peak_rss_mb": round(s1["maxrss"] / MB, 1),
        "minflt": s1["minflt"] - s0["minflt"], "majflt": s1["majflt"] - s0["majflt"],
        "disk_read_mb": round((s1["io_read_bytes"] - s0["io_read_bytes"]) / MB, 1),
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    new = not os.path.exists(a.out)
    with open(a.out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if new:
            w.writeheader()
        w.writerow(row)
    print(row)


if __name__ == "__main__":
    main()