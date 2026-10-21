"""Compara read() x mmap: tempo, RSS, VSZ, faltas de pagina, E/S, MemAvailable."""
import argparse, csv, os, subprocess, time, datetime, sys
import store

def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "n/a"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--mode", choices=["read", "mmap"], required=True)
    ap.add_argument("--pattern", choices=["seq", "rand"], default="seq")
    ap.add_argument("--label", default="")          # cold / warm
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--out", default="results/raw/c1_c2.csv")
    a = ap.parse_args()

    commit = git_commit()                            # antes de medir
    size = os.path.getsize(a.file)
    m0 = store.meminfo()
    s0 = store.snapshot()

    fn = store.read_conventional if a.mode == "read" else store.read_mmap
    nbytes, t_open, t_read, s1 = fn(a.file, a.pattern)

    m1 = store.meminfo()
    MB = 1048576
    row = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": commit, "python": sys.version.split()[0],
        "file": os.path.basename(a.file), "size_mb": round(size / MB, 1),
        "mode": a.mode, "pattern": a.pattern, "label": a.label, "rep": a.rep,
        "open_s": round(t_open, 6), "read_s": round(t_read, 6),
        "total_s": round(t_open + t_read, 6), "bytes": nbytes,
        "rss_before_mb": round(s0["rss"] / MB, 1),
        "rss_mb": round(s1["rss"] / MB, 1),
        "peak_rss_mb": round(s1["maxrss"] / MB, 1),
        "vsz_mb": round(s1["vms"] / MB, 1),
        "minflt": s1["minflt"] - s0["minflt"],
        "majflt": s1["majflt"] - s0["majflt"],
        "disk_read_mb": round((s1["io_read_bytes"] - s0["io_read_bytes"]) / MB, 1),
        "memavail_before_mb": round(m0["MemAvailable"] / MB),
        "memavail_after_mb": round(m1["MemAvailable"] / MB),
        "cached_before_mb": round(m0["Cached"] / MB),
        "cached_after_mb": round(m1["Cached"] / MB),
        "swap_used_mb": round((m1["SwapTotal"] - m1["SwapFree"]) / MB),
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