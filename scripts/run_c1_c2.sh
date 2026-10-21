#!/usr/bin/env bash
# C1 (read) e C2 (mmap): 3 tamanhos x 2 modos x 2 padroes x (fria, quente) x 3 repeticoes = 72 execucoes.
# Uso: bash scripts/run_c1_c2.sh      (ambiente em repouso; pede a senha do sudo uma vez)
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
SIZES=${SIZES:-"10 100 500"}
sudo -v
OUT=results/raw/c1_c2_$(date +%Y%m%d_%H%M%S).csv
mkdir -p results/raw data

for size in $SIZES; do
  F=data/corpus_${size}mb.txt
  [ -f "$F" ] || python src/gen_corpus.py --size-mb $size --out "$F"
  for mode in read mmap; do
    for pattern in seq rand; do
      for rep in 1 2 3; do
        sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
        python src/memtest.py --file "$F" --mode $mode --pattern $pattern --label cold --rep $rep --out "$OUT" > /dev/null
        python src/memtest.py --file "$F" --mode $mode --pattern $pattern --label warm --rep $rep --out "$OUT" > /dev/null
      done
    done
  done
done
echo "Resultados em $OUT ($(($(wc -l < "$OUT") - 1)) execucoes)"