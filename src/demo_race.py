"""Parte D - demonstracao controlada de condicao de corrida e correcao.

Tres experimentos, cada um em tres modos (3 repeticoes):
  A) estrutura do cache (contadores e OrderedDict): sem lock x com mutex
  B) computacao duplicada ("cache stampede"): sem lock x mutex x single-flight
  C) log concorrente: sem lock x com lock (linhas corrompidas)

Uso (a partir da raiz do repositorio):
  python src/demo_race.py --reps 3 --out results/raw/d_race.csv
"""
import argparse, csv, json, os, sys, tempfile, threading, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cache import SharedCache
from logger import EventLog


class SingleFlight:
    """Evita que dois consumidores calculem a mesma consulta ao mesmo tempo.
    O lock protege so o mapa de consultas em andamento, nunca o calculo."""
    def __init__(self):
        self._lock = threading.Lock()
        self._inflight = {}                      # chave -> Event

    def begin(self, key):
        with self._lock:
            ev = self._inflight.get(key)
            if ev is None:
                self._inflight[key] = threading.Event()
                return True, None                # esta thread calcula
            return False, ev                     # outra thread ja esta calculando

    def end(self, key):
        with self._lock:
            ev = self._inflight.pop(key)
        ev.set()


def run_threads(n, target):
    ts = [threading.Thread(target=target, args=(i,), name=f"w{i}") for i in range(n)]
    t0 = time.perf_counter()
    for t in ts: t.start()
    for t in ts: t.join()
    return time.perf_counter() - t0


def exp_a(mode, nthreads, nops, keys, cap):
    """Contadores e estrutura: esperado hits+misses == nthreads*nops."""
    cache = SharedCache(capacity=cap, policy="lru", locked=(mode == "mutex"))
    errors = Counter()

    def worker(i):
        for j in range(nops):
            k = (i * 7 + j * 13) % keys
            try:
                if cache.get(k) is None:
                    cache.put(k, k, 0.001)
            except Exception as e:               # KeyError etc. por estrutura corrompida
                errors[type(e).__name__] += 1

    wall = run_threads(nthreads, worker)
    gets = nthreads * nops - sum(errors.values())
    st = cache.stats()
    return {"wall_s": round(wall, 4), "esperado": gets, "observado": st["hits"] + st["misses"],
            "atualizacoes_perdidas": gets - (st["hits"] + st["misses"]),
            "tam_final": st["size"], "capacidade": cap,
            "acima_capacidade": max(0, st["size"] - cap),
            "excecoes": sum(errors.values()), "tipos_excecao": json.dumps(dict(errors))}


def exp_a2(mode, nthreads, nops):
    """Atualizacao perdida: contador compartilhado com ler -> (troca de thread) -> gravar."""
    cache = SharedCache(capacity=1, locked=(mode == "mutex"))
    lock = threading.Lock() if mode == "mutex" else None

    def worker(i):
        for _ in range(nops):
            if lock: lock.acquire()
            tmp = cache.hits            # le
            time.sleep(0)               # cede a CPU (ponto de troca de contexto)
            cache.hits = tmp + 1        # grava valor possivelmente velho
            if lock: lock.release()

    wall = run_threads(nthreads, worker)
    esperado = nthreads * nops
    return {"wall_s": round(wall, 4), "esperado": esperado, "observado": cache.hits,
            "atualizacoes_perdidas": esperado - cache.hits}


def exp_b(mode, nthreads, uniq, calc_s):
    """Todas as threads pedem as mesmas 'uniq' consultas; minimo de calculos = uniq."""
    cache = SharedCache(capacity=uniq * 2, policy="lru", locked=(mode != "unsafe"))
    sf = SingleFlight()
    computed = Counter()
    clock = threading.Lock()

    def compute(k):
        time.sleep(calc_s)                       # custo da recuperacao/geracao
        with clock:
            computed[k] += 1
        return k

    def worker(i):
        for k in range(uniq):
            if cache.get(k) is not None:
                continue
            if mode == "singleflight":
                lead, ev = sf.begin(k)
                if not lead:
                    ev.wait()
                    continue
                try:
                    if cache.get(k) is None:
                        cache.put(k, compute(k), calc_s)
                finally:
                    sf.end(k)
            else:
                cache.put(k, compute(k), calc_s)

    wall = run_threads(nthreads, worker)
    total = sum(computed.values())
    return {"wall_s": round(wall, 4), "calculos": total, "minimo": uniq,
            "calculos_duplicados": total - uniq}


def exp_c(mode, nthreads, nlines):
    path = os.path.join(tempfile.gettempdir(), f"demo_log_{mode}.log")
    log = EventLog(path, locked=(mode == "lock"))
    payload = "x" * 6000                         # linha grande: escrita passa do buffer

    def emit(i, j):
        # como muitos loggers: cabecalho e corpo em duas escritas separadas
        head = f"{time.time():.6f}\t{threading.current_thread().name}\tevento\t"
        body = json.dumps({"thread": i, "seq": j, "dados": payload}) + "\n"
        with log._lock:
            log.f.write(head)
            time.sleep(0)
            log.f.write(body)

    def worker(i):
        for j in range(nlines):
            emit(i, j)

    wall = run_threads(nthreads, worker)
    log.close()
    ok = bad = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t", 3)
            try:
                assert len(p) == 4
                json.loads(p[3]); ok += 1
            except Exception:
                bad += 1
    return {"wall_s": round(wall, 4), "linhas_esperadas": nthreads * nlines,
            "linhas_validas": ok, "linhas_corrompidas": bad}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out", default="results/raw/d_race.csv")
    ap.add_argument("--switch", type=float, default=1e-6,
                    help="sys.setswitchinterval: forca trocas de thread frequentes")
    a = ap.parse_args()
    sys.setswitchinterval(a.switch)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    rows = []
    for rep in range(1, a.reps + 1):
        for mode in ("unsafe", "mutex"):
            rows.append({"exp": "A_estrutura", "modo": mode, "rep": rep,
                         **exp_a(mode, a.threads, 20000, keys=30, cap=10)})
        for mode in ("unsafe", "mutex"):
            rows.append({"exp": "A2_atualizacao_perdida", "modo": mode, "rep": rep,
                         **exp_a2(mode, a.threads, 20000)})
        for mode in ("unsafe", "mutex", "singleflight"):
            rows.append({"exp": "B_duplicacao", "modo": mode, "rep": rep,
                         **exp_b(mode, a.threads, uniq=20, calc_s=0.005)})
        for mode in ("unsafe", "lock"):
            rows.append({"exp": "C_log", "modo": mode, "rep": rep,
                         **exp_c(mode, a.threads, 300)})
    cols = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("exp", "modo", "rep"), k))
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    for r in rows:
        print({k: v for k, v in r.items() if v != ""})
    print("gravado em", a.out)


if __name__ == "__main__":
    main()