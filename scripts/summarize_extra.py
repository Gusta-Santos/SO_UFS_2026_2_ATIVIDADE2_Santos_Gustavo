"""Resume C1/C2, C5 e C6 (media e desvio padrao das repeticoes) em results/tables/."""
import glob, os
import pandas as pd

os.makedirs("results/tables", exist_ok=True)
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)


def agg(df, keys, cols):
    g = df.groupby(keys)[cols].agg(["mean", "std"]).round(3)
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    g["n_reps"] = df.groupby(keys).size()
    return g


files = sorted(glob.glob("results/raw/c1_c2_*.csv"))
if files:
    d = pd.read_csv(files[-1])
    t = agg(d, ["size_mb", "pattern", "mode", "label"],
            ["open_s", "read_s", "rss_mb", "peak_rss_mb", "vsz_mb", "minflt", "majflt",
             "disk_read_mb", "cached_after_mb"])
    t.to_csv("results/tables/c1_c2_summary.csv"); print("== C1/C2 (", files[-1], ") =="); print(t)

if os.path.exists("results/raw/c5.csv"):
    d = pd.read_csv("results/raw/c5.csv")
    t = agg(d, ["label"], ["index_mb", "index_load_s", "retr_mean_ms", "lat_p95_ms", "peak_rss_mb",
                           "minflt", "majflt", "disk_read_mb", "memavail_after_mb", "swap_used_mb"])
    t.to_csv("results/tables/c5_summary.csv"); print("== C5 =="); print(t)

if os.path.exists("results/raw/c6.csv"):
    d = pd.read_csv("results/raw/c6.csv")
    t = agg(d, ["label"], ["nreq", "processed", "errors", "lost", "dropped", "put_timeouts",
                           "gen_retries", "queue_max"])
    t.to_csv("results/tables/c6_summary.csv"); print("== C6 =="); print(t)