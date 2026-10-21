"""GenResearch-Servidor: produtores -> fila -> consumidores (cache -> recuperacao -> geracao),
com log de eventos e metricas. Uma execucao = uma linha em results/raw/server_runs.csv."""
import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")   # BLAS com 1 thread: a concorrencia vem so das threads do servidor

import argparse, csv, datetime, queue, random, subprocess, sys, threading, time
import numpy as np
import store, vecstore
from cache import SharedCache
from generate import ExternalServiceError, generate
from logger import EventLog
from retrieve import Retriever


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "n/a"


def build_queries(workload, n, uniq, seed):
    rnd = random.Random(seed)
    vocab = [f"termo{i}" for i in range(vecstore.VOCAB)]
    mk = lambda: " ".join(rnd.choices(vocab, k=6))
    if workload == "repeated":                      # poucas consultas, muito repetidas
        pool = [mk() for _ in range(uniq)]
        return [rnd.choice(pool) for _ in range(n)]
    return [mk() for _ in range(n)]                 # distinct: todas diferentes


def producer(items, q, log, a, put_timeouts, dropped):
    for rid, query in items:
        item = (rid, query, time.perf_counter())
        tries = 0
        while True:
            try:
                q.put(item, timeout=a.put_timeout)      # timeout=None: bloqueia ate ter espaco
                log.log("enfileirar", id=rid, fila=q.qsize())
                break
            except queue.Full:                          # fila saturada
                tries += 1
                put_timeouts.append(rid)
                log.log("fila_cheia", id=rid, tentativa=tries)
                if tries > a.put_retries:
                    dropped.append(rid)                 # descarte controlado e registrado
                    log.log("descartada", id=rid)
                    break
                time.sleep(a.retry_wait_ms / 1000.0)


def worker(wid, q, cache, retr, args, log, results):
    while True:
        item = q.get()
        if item is None:                            # sentinela de encerramento
            break
        rid, query, t_sub = item
        t_start = time.perf_counter()
        key = " ".join(query.split())
        rec = {"id": rid, "wid": wid, "wait": t_start - t_sub, "hit": False,
               "retr": 0.0, "gen": 0.0, "err": "", "retries": 0}
        try:
            log.log("consulta", id=rid, worker=wid, espera_ms=round(rec["wait"] * 1000, 2))
            val = cache.get(key)
            if val is not None:
                rec["hit"] = True
                log.log("cache_acerto", id=rid)
            else:
                log.log("cache_erro", id=rid)
                t1 = time.perf_counter()
                ctx, nbytes = retr.search(query, args.k, args.max_ctx)
                t2 = time.perf_counter()
                log.log("recuperacao", id=rid, trechos=len(ctx), bytes=nbytes,
                        tokens_aprox=sum(len(c.split()) for c in ctx),
                        ms=round((t2 - t1) * 1000, 2))
                ans = None
                for attempt in range(args.gen_retries + 1):
                    try:
                        ans = generate(query, ctx, args.gen_cpu, args.gen_io_ms, args.gen_fail_rate)
                        break
                    except ExternalServiceError as e:
                        rec["retries"] += 1
                        log.log("retentativa", id=rid, tentativa=attempt + 1, erro=str(e))
                        time.sleep(0.01 * (2 ** attempt))       # recuo exponencial
                if ans is None:
                    raise RuntimeError("servico externo indisponivel apos retentativas")
                t3 = time.perf_counter()
                log.log("geracao", id=rid, ms=round((t3 - t2) * 1000, 2), resumo=ans[:50])
                cache.put(key, ans, t3 - t1)
                rec["retr"], rec["gen"] = t2 - t1, t3 - t2
        except Exception as e:
            rec["err"] = repr(e)
            log.log("falha", id=rid, erro=repr(e))
        t_end = time.perf_counter()
        rec["svc"], rec["lat"], rec["t_end"] = t_end - t_start, t_end - t_sub, t_end
        results.append(rec)                         # list.append e atomico em CPython


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--nreq", type=int, default=200)
    ap.add_argument("--workload", choices=["repeated", "distinct"], default="distinct")
    ap.add_argument("--uniq", type=int, default=20, help="consultas unicas (workload repeated)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--producers", type=int, default=2)
    ap.add_argument("--queue-size", type=int, default=50, help="0 = ilimitada")
    ap.add_argument("--cache-size", type=int, default=0, help="0 = sem cache")
    ap.add_argument("--cache-policy", choices=["lru", "fifo"], default="lru")
    ap.add_argument("--vec-mode", choices=["mmap", "ram"], default="mmap")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--max-ctx", type=int, default=2000, help="bytes de contexto")
    ap.add_argument("--gen-cpu", type=int, default=20000, help="iteracoes de CPU por KB de contexto")
    ap.add_argument("--gen-io-ms", type=float, default=20.0, help="espera de E/S simulada por resposta")
    ap.add_argument("--put-timeout", type=float, default=None, help="s; None = produtor bloqueia")
    ap.add_argument("--put-retries", type=int, default=3)
    ap.add_argument("--retry-wait-ms", type=float, default=50.0)
    ap.add_argument("--gen-fail-rate", type=float, default=0.0, help="prob. de falha do servico externo")
    ap.add_argument("--gen-retries", type=int, default=2)
    ap.add_argument("--mem-limit-mb", type=int, default=0,
                    help="limite de memoria virtual ADICIONAL (RLIMIT_AS), usado no C6; 0 = sem limite")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--label", default="run")
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--out", default="results/raw/server_runs.csv")
    ap.add_argument("--log", default=None)
    ap.add_argument("--no-cache-lock", action="store_true", help="so para a demo da Parte D")
    ap.add_argument("--no-log-lock", action="store_true", help="so para a demo da Parte D")
    a = ap.parse_args()

    commit = git_commit()
    log = EventLog(a.log or f"results/logs/{a.label}_rep{a.rep}.log", locked=not a.no_log_lock)
    log.log("inicio", **{k: v for k, v in vars(a).items() if k not in ("out", "log")})
    m0, s0 = store.meminfo(), store.snapshot()

    if a.mem_limit_mb:                              # limite explicito de memoria (C6)
        import resource
        lim = store.snapshot()["vms"] + a.mem_limit_mb * 1048576
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
        log.log("limite_memoria", adicional_mb=a.mem_limit_mb)
    t_load = time.perf_counter()
    try:
        retr = Retriever(a.index, a.vec_mode)
    except Exception as e:
        log.log("falha", etapa="abrir_indice", erro=repr(e))
        log.log("encerramento", status="erro")
        log.close()
        print("ERRO ao abrir o indice:", repr(e))
        sys.exit(2)
    index_load_s = time.perf_counter() - t_load
    meta = vecstore.load_meta(a.index)

    cache = SharedCache(a.cache_size, a.cache_policy, locked=not a.no_cache_lock)
    q = queue.Queue(maxsize=a.queue_size)
    results, put_timeouts, dropped = [], [], []
    items = list(enumerate(build_queries(a.workload, a.nreq, a.uniq, a.seed)))

    samples, stop = [], threading.Event()
    def sampler():
        while not stop.is_set():
            samples.append(q.qsize())
            time.sleep(0.005)

    workers = [threading.Thread(target=worker, name=f"consumidor-{i}",
                                args=(i, q, cache, retr, a, log, results)) for i in range(a.workers)]
    prods = [threading.Thread(target=producer, name=f"produtor-{i}",
                              args=(items[i::a.producers], q, log, a, put_timeouts, dropped)) for i in range(a.producers)]
    smp = threading.Thread(target=sampler, name="monitor-fila", daemon=True)

    t0 = time.perf_counter()
    for t in workers + prods + [smp]:
        t.start()
    threads_peak = threading.active_count()
    for t in prods:
        t.join()
    for _ in workers:
        q.put(None)
    for t in workers:
        t.join()
    wall = time.perf_counter() - t0
    stop.set()
    s1, m1 = store.snapshot(), store.meminfo()

    ok = [r for r in results if not r["err"]]
    lat = np.array([r["lat"] for r in ok]) if ok else np.array([0.0])
    ids = [r["id"] for r in results]
    order = [r["id"] for r in sorted(results, key=lambda r: r["t_end"])]
    cs, MB = cache.stats(), 1048576
    mean_ms = lambda key: round(1000 * float(np.mean([r[key] for r in ok])), 3) if ok else 0
    row = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"), "commit": commit,
        "label": a.label, "rep": a.rep, "workers": a.workers, "producers": a.producers,
        "queue_size": a.queue_size, "nreq": a.nreq, "workload": a.workload, "uniq": a.uniq,
        "cache_size": a.cache_size, "cache_policy": a.cache_policy, "vec_mode": a.vec_mode,
        "k": a.k, "max_ctx": a.max_ctx, "gen_cpu": a.gen_cpu, "gen_io_ms": a.gen_io_ms,
        "index": os.path.basename(a.index.rstrip("/")), "n_chunks": meta["n_chunks"],
        "index_mb": round(sum(vecstore.size_mb(p) for p in vecstore.paths(a.index)[:2]
                              if os.path.exists(p)), 1),
        "index_load_s": round(index_load_s, 4),
        "wall_s": round(wall, 4), "throughput_rps": round(len(ok) / wall, 2),
        "lat_mean_ms": round(1000 * float(lat.mean()), 3),
        "lat_median_ms": round(1000 * float(np.median(lat)), 3),
        "lat_p95_ms": round(1000 * float(np.percentile(lat, 95)), 3),
        "svc_mean_ms": mean_ms("svc"), "wait_mean_ms": mean_ms("wait"),
        "retr_mean_ms": mean_ms("retr"), "gen_mean_ms": mean_ms("gen"),
        "queue_avg": round(float(np.mean(samples)), 2) if samples else 0,
        "queue_max": max(samples) if samples else 0,
        "worker_util": round(sum(r["svc"] for r in results) / (a.workers * wall), 3),
        "threads_peak": threads_peak,
        "processed": len(results), "errors": len(results) - len(ok),
        "lost": a.nreq - len(set(ids)), "duplicated": len(ids) - len(set(ids)),
        "out_of_order": sum(1 for x, y in zip(order, order[1:]) if y < x),
        "put_timeouts": len(put_timeouts), "dropped": len(dropped),
        "gen_retries": sum(r["retries"] for r in results),
        "cache_hits": cs["hits"], "cache_misses": cs["misses"], "hit_rate": cs["hit_rate"],
        "evictions": cs["evictions"], "cache_saved_s": cs["saved_s"],
        "rss_mb": round(s1["rss"] / MB, 1), "peak_rss_mb": round(s1["maxrss"] / MB, 1),
        "vsz_mb": round(s1["vms"] / MB, 1),
        "minflt": s1["minflt"] - s0["minflt"], "majflt": s1["majflt"] - s0["majflt"],
        "disk_read_mb": round((s1["io_read_bytes"] - s0["io_read_bytes"]) / MB, 1),
        "memavail_before_mb": round(m0["MemAvailable"] / MB),
        "memavail_after_mb": round(m1["MemAvailable"] / MB),
        "cached_after_mb": round(m1["Cached"] / MB),
        "swap_used_mb": round((m1["SwapTotal"] - m1["SwapFree"]) / MB),
    }
    log.log("encerramento", status="ok", processadas=len(results), erros=row["errors"], wall_s=row["wall_s"])
    log.close()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    new = not os.path.exists(a.out)
    with open(a.out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if new:
            w.writeheader()
        w.writerow(row)
    print({k: row[k] for k in ("label", "workers", "wall_s", "throughput_rps", "lat_median_ms",
                               "lat_p95_ms", "hit_rate", "queue_max", "processed", "errors", "lost", "duplicated")})


if __name__ == "__main__":
    main()