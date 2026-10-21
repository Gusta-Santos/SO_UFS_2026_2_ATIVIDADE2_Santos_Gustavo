#!/usr/bin/env bash
# C6: falhas controladas. Cada cenario deve terminar de forma controlada (log + codigo de saida), nunca travar.
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
IDX=${IDX:-data/index_100mb}
mkdir -p results/raw results/logs
OUT=results/raw/c6.csv
SEMDB=${IDX}_semdb
rm -rf "$SEMDB"; cp -r "$IDX" "$SEMDB"; rm -f "$SEMDB/chunks.db"      # indice com o banco indisponivel

run() {   # descricao, depois os argumentos do server.py
  desc=$1; shift
  echo "== $desc =="
  for rep in 1 2 3; do
    timeout 300 python src/server.py "$@" --rep $rep --out $OUT
    rc=$?
    echo "$desc | rep $rep | codigo de saida: $rc" | tee -a results/logs/c6_saidas.txt
  done
}

run "a) arquivo/indice ausente" --index data/nao_existe --nreq 20 --label c6_a_ausente
run "b) banco do indice indisponivel (falha por requisicao)" --index "$SEMDB" --nreq 50 --workers 2 --label c6_b_banco
run "c) fila saturada: timeout + retentativas + descarte" --index "$IDX" --nreq 100 --workers 1 --producers 4 \
    --queue-size 2 --gen-io-ms 100 --put-timeout 0.05 --put-retries 2 --retry-wait-ms 30 --label c6_c_fila
run "d) servico externo com 30% de falha + retentativas" --index "$IDX" --nreq 200 --workers 2 \
    --gen-fail-rate 0.3 --gen-retries 2 --label c6_d_externo
run "e1) limite de memoria (100 MB adicionais) com indice em RAM" --index "$IDX" --vec-mode ram --mem-limit-mb 100 \
    --nreq 20 --label c6_e1_limite_baixo
run "e2) limite de memoria (600 MB adicionais) com indice em RAM" --index "$IDX" --vec-mode ram --mem-limit-mb 600 \
    --nreq 20 --label c6_e2_limite_ok
rm -rf "$SEMDB"
echo "Concluido: $OUT"