"""Compara read() x mmap: tempo, RSS, VSZ, faltas de pagina, MemAvailable."""
import argparse, csv, os, time, datetime
import store

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--mode", choices=["read", "mmap"], required=True)
    ap.add_argument("--pattern", choices=["seq", "rand"], default="seq")
    ap.add_argument("--label", default="")
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--out", default="results/memtest.csv")
    a = ap.parse_args()

    size = os.path.getsize(a.file)
    m0 = store.meminfo()
    s0 = store.snapshot()

    t0 = time.perf_counter()
    fn = store.read_conventional if a.mode == "read" else store.read_mmap
    nbytes = fn(a.file, a.pattern)
    t1 = time.perf_counter()

    s1 = store.snapshot()
    m1 = store.meminfo()

    row = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "file": os.path.basename(a.file), "size_mb": round(size/1048576, 1),
        "mode": a.mode, "pattern": a.pattern, "label": a.label, "rep": a.rep,
        "read_s": round(t1 - t0, 6), "bytes": nbytes,
        "rss_mb": round(s1["rss"]/1048576, 1),
        "vsz_mb": round(s1["vms"]/1048576, 1),
        "minflt": s1["minflt"] - s0["minflt"],
        "majflt": s1["majflt"] - s0["majflt"],
        "memavail_before_mb": round(m0["MemAvailable"]/1048576),
        "memavail_after_mb": round(m1["MemAvailable"]/1048576),
        "cached_before_mb": round(m0["Cached"]/1048576),
        "cached_after_mb": round(m1["Cached"]/1048576),
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
