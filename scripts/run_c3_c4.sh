#!/usr/bin/env bash
# Baterias oficiais C3 (concorrencia e fila) e C4 (cache compartilhado).
# Uso: bash scripts/run_c3_c4.sh      (WSL em repouso, sem outros programas pesados)
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
IDX=${IDX:-data/index_100mb}
N3=${N3:-300}      # requisicoes por execucao do C3
N4=${N4:-400}      # requisicoes por execucao do C4
mkdir -p results/raw results/logs

echo "== aquecimento (descartado) =="
python src/server.py --index "$IDX" --nreq 50 --workers 2 --label warmup --out results/raw/warmup.csv > /dev/null
rm -f results/raw/warmup.csv results/logs/warmup_*

echo "== C3: 1, 2 e 4 trabalhadores; cenarios io (E/S domina) e cpu (CPU domina) =="
for scen in io cpu; do
  if [ "$scen" = io ]; then GEN="--gen-cpu 20000 --gen-io-ms 20"; else GEN="--gen-cpu 100000 --gen-io-ms 0"; fi
  for w in 1 2 4; do
    for rep in 1 2 3; do
      python src/server.py --index "$IDX" --nreq "$N3" --workers $w --producers 2 --queue-size 50 \
        --workload distinct --cache-size 0 $GEN --label c3_${scen}_w${w} --rep $rep --out results/raw/c3.csv
    done
  done
done

echo "== C4: cache com consultas repetidas x distintas (2 trabalhadores) =="
run4() {   # workload tamanho politica
  for rep in 1 2 3; do
    python src/server.py --index "$IDX" --nreq "$N4" --workers 2 --producers 2 --queue-size 50 \
      --workload $1 --uniq 20 --cache-size $2 --cache-policy $3 \
      --label c4_$1_s$2_$3 --rep $rep --out results/raw/c4.csv
  done
}
run4 repeated 0 lru
for s in 10 20 40; do for p in lru fifo; do run4 repeated $s $p; done; done
run4 distinct 0 lru
run4 distinct 20 lru
echo "Concluido: results/raw/c3.csv e results/raw/c4.csv"