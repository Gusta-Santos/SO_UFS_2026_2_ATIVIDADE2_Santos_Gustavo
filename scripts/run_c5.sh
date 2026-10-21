#!/usr/bin/env bash
# C5: pressao de memoria. Aumenta o indice (corpus) e compara mmap x ram, com vmstat em paralelo.
# Limites de seguranca: WSL limitado pelo .wslconfig; o modo ram e PULADO quando o indice nao cabe na RAM.
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
SIZES=${SIZES:-"100 1000 2500"}
MIN_MARGIN_MB=400
mkdir -p results/raw results/logs
sudo -v

for sz in $SIZES; do
  IDX=data/index_${sz}mb
  [ -d "$IDX" ] || { echo "ERRO: falta $IDX (gere o corpus e rode ingest.py)"; exit 1; }
  NREQ=30; [ "$sz" -ge 2000 ] && NREQ=10
  VEC_MB=$(python -c "import os;print(int(os.path.getsize('$IDX/vectors.f32')/1048576))")
  for mode in mmap ram; do
    AVAIL_MB=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
    if [ "$mode" = ram ] && [ $((VEC_MB + MIN_MARGIN_MB)) -gt "$AVAIL_MB" ]; then
      echo "PULADO: ram com ${sz}MB (vetores ${VEC_MB} MB + margem ${MIN_MARGIN_MB} MB > disponivel ${AVAIL_MB} MB)"
      echo "${sz},${mode},pulado,${VEC_MB},${AVAIL_MB}" >> results/raw/c5_pulados.csv
      continue
    fi
    for rep in 1 2 3; do
      sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null      # cada execucao comeca com cache frio
      vmstat 1 > results/vmstat_c5_${sz}_${mode}_rep${rep}.txt &
      VM=$!
      python src/server.py --index "$IDX" --nreq $NREQ --workers 1 --producers 1 --queue-size 50 \
        --workload distinct --cache-size 0 --gen-cpu 0 --gen-io-ms 0 --vec-mode $mode \
        --label c5_${sz}_${mode} --rep $rep --out results/raw/c5.csv
      kill $VM 2>/dev/null || true; wait $VM 2>/dev/null || true
    done
  done
done
echo "Concluido: results/raw/c5.csv (e c5_pulados.csv, se houve modo ram pulado)"