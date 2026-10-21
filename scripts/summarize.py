"""Resume c3.csv e c4.csv (media e desvio padrao das repeticoes) em results/tables/."""
import os
import pandas as pd

os.makedirs("results/tables", exist_ok=True)


def agg(df, cols):
    g = df.groupby("label")[cols].agg(["mean", "std"]).round(2)
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    g["n_reps"] = df.groupby("label").size()
    return g


# ---- C3 ----
c3 = pd.read_csv("results/raw/c3.csv")
s3 = agg(c3, ["throughput_rps", "svc_mean_ms", "lat_median_ms", "lat_p95_ms", "queue_avg",
              "queue_max", "worker_util", "errors", "lost", "duplicated", "out_of_order"])
s3["scenario"] = [l.split("_")[1] for l in s3.index]
s3["workers"] = [int(l.split("_w")[1]) for l in s3.index]
base = s3[s3.workers == 1].set_index("scenario")["throughput_rps_mean"]
s3["speedup"] = (s3["throughput_rps_mean"] / s3["scenario"].map(base)).round(2)
s3["efficiency"] = (s3["speedup"] / s3["workers"]).round(2)
s3.to_csv("results/tables/c3_summary.csv")
print("== C3 ==")
print(s3[["throughput_rps_mean", "throughput_rps_std", "svc_mean_ms_mean", "lat_p95_ms_mean",
          "speedup", "efficiency"]])

# ---- C4 ----
c4 = pd.read_csv("results/raw/c4.csv")
s4 = agg(c4, ["hit_rate", "cache_hits", "cache_misses", "evictions", "cache_saved_s",
              "throughput_rps", "wall_s", "lat_p95_ms"])
uniq = int(c4.iloc[0]["uniq"])
s4["workload"] = [l.split("_")[1] for l in s4.index]
s4["cache_size"] = [int(l.split("_s")[1].split("_")[0]) for l in s4.index]
s4["policy"] = [l.split("_")[-1] for l in s4.index]
# misses alem do minimo possivel (uniq) quando o cache comporta tudo: so podem ser calculos duplicados
mask = (s4.workload == "repeated") & (s4.cache_size >= uniq)
s4["misses_acima_do_minimo"] = (s4["cache_misses_mean"] - uniq).where(mask).round(2)
s4.to_csv("results/tables/c4_summary.csv")
print("== C4 ==")
print(s4[["hit_rate_mean", "hit_rate_std", "evictions_mean", "cache_saved_s_mean",
          "throughput_rps_mean", "misses_acima_do_minimo"]])