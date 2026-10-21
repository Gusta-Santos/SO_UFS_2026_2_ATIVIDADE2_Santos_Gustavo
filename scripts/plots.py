"""Graficos da Parte C em results/figures/. Uso: python scripts/plots.py"""
import glob, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

os.makedirs("results/figures", exist_ok=True)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"results/figures/{name}", dpi=150)
    plt.close(fig)
    print("gerado: results/figures/" + name)


# ---------- C3: concorrencia ----------
if os.path.exists("results/raw/c3.csv"):
    d = pd.read_csv("results/raw/c3.csv")
    d["scenario"] = d.label.str.split("_").str[1]
    g = d.groupby(["scenario", "workers"]).agg(thr=("throughput_rps", "mean"), thr_sd=("throughput_rps", "std"),
                                               svc=("svc_mean_ms", "mean"), svc_sd=("svc_mean_ms", "std")).reset_index()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for sc, gg in g.groupby("scenario"):
        ax[0].errorbar(gg.workers, gg.thr, yerr=gg.thr_sd.fillna(0), marker="o", capsize=3, label=f"cenario {sc}")
        ax[0].plot(gg.workers, gg.thr.iloc[0] * gg.workers / gg.workers.iloc[0], "--", alpha=0.4, color="gray")
        ax[1].errorbar(gg.workers, gg.svc, yerr=gg.svc_sd.fillna(0), marker="o", capsize=3, label=f"cenario {sc}")
    ax[0].set(xlabel="trabalhadores (threads)", ylabel="vazao (req/s)", title="C3: vazao x trabalhadores (tracejado = escala ideal)",
              xticks=sorted(d.workers.unique()))
    ax[1].set(xlabel="trabalhadores (threads)", ylabel="tempo de servico medio (ms)", title="C3: tempo de servico por requisicao",
              xticks=sorted(d.workers.unique()))
    for a in ax:
        a.legend(); a.grid(alpha=0.3)
    save(fig, "c3_concorrencia.png")

# ---------- C4: cache ----------
if os.path.exists("results/raw/c4.csv"):
    d = pd.read_csv("results/raw/c4.csv")
    d["workload"] = d.label.str.split("_").str[1]
    d["size"] = d.label.str.extract(r"_s(\d+)_")[0].astype(int)
    d["policy"] = d.label.str.split("_").str[-1]
    g = d.groupby(["workload", "size", "policy"]).agg(hit=("hit_rate", "mean"), hit_sd=("hit_rate", "std"),
                                                      thr=("throughput_rps", "mean"), thr_sd=("throughput_rps", "std")).reset_index()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    rep = g[g.workload == "repeated"]
    for pol in ("lru", "fifo"):
        gg = rep[(rep.policy == pol) | (rep["size"] == 0)].sort_values("size")
        ax[0].errorbar(gg["size"], gg.hit, yerr=gg.hit_sd.fillna(0), marker="o", capsize=3, label=pol.upper())
    ax[0].set(xlabel="tamanho do cache (entradas)", ylabel="taxa de acerto", title="C4: acerto x tamanho (20 consultas unicas)")
    ax[0].legend(); ax[0].grid(alpha=0.3)
    g["nome"] = g.workload.str[:4] + " c=" + g["size"].astype(str) + " " + g.policy
    g = g.sort_values(["workload", "size", "policy"])
    ax[1].bar(g.nome, g.thr, yerr=g.thr_sd.fillna(0), capsize=2)
    ax[1].set_yscale("log"); ax[1].set(ylabel="vazao (req/s, escala log)", title="C4: vazao por configuracao")
    ax[1].tick_params(axis="x", rotation=60); ax[1].grid(alpha=0.3, axis="y")
    save(fig, "c4_cache.png")

# ---------- C1/C2: read x mmap ----------
files = sorted(glob.glob("results/raw/c1_c2_*.csv"))
if files:
    d = pd.read_csv(files[-1])
    for pat in sorted(d.pattern.unique()):
        dd = d[d.pattern == pat]
        fig, ax = plt.subplots(1, 3, figsize=(14, 4))
        for a, col, title, log in ((ax[0], "total_s", "tempo total (abrir + ler), s", True),
                                   (ax[1], "minflt", "faltas de pagina minor", True),
                                   (ax[2], "majflt", "faltas de pagina major", False)):
            pv = dd.pivot_table(index="size_mb", columns=["mode", "label"], values=col, aggfunc="mean")
            pv.columns = [f"{m} {l}" for m, l in pv.columns]
            pv.plot(kind="bar", ax=a, logy=log, rot=0)
            a.set(xlabel="tamanho do corpus (MB)", title=f"{title} ({pat})"); a.grid(alpha=0.3, axis="y")
        save(fig, f"c1_c2_{pat}.png")

# ---------- C5: pressao de memoria ----------
if os.path.exists("results/raw/c5.csv"):
    d = pd.read_csv("results/raw/c5.csv")
    d["size"] = d.label.str.split("_").str[1].astype(int)
    d["mode"] = d.label.str.split("_").str[2]
    g = d.groupby(["mode", "size"]).agg(retr=("retr_mean_ms", "mean"), retr_sd=("retr_mean_ms", "std"),
                                       maj=("majflt", "mean"), disk=("disk_read_mb", "mean")).reset_index()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for mode, gg in g.groupby("mode"):
        ax[0].errorbar(gg["size"], gg.retr, yerr=gg.retr_sd.fillna(0), marker="o", capsize=3, label=mode)
        ax[1].plot(gg["size"], gg.disk, marker="o", label=mode)
    ax[0].set(xlabel="tamanho do corpus (MB)", ylabel="recuperacao media (ms)", title="C5: custo da recuperacao", xscale="log", yscale="log")
    ax[1].set(xlabel="tamanho do corpus (MB)", ylabel="MB lidos do disco (sistema)", title="C5: leitura de disco por execucao", xscale="log")
    for a in ax:
        a.legend(); a.grid(alpha=0.3)
    save(fig, "c5_pressao.png")