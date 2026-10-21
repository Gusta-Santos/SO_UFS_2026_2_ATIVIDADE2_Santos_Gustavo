# Comandos executados (ordem de execução)

Repositório: [[URL do GitHub](https://github.com/Gusta-Santos/SO_UFS_2026_2_ATIVIDADE2_Santos_Gustavo)]
Ambiente: WSL2, Ubuntu 22.04.5, Python 3.10.12, `.wslconfig` com 4 GB de RAM, 4 CPUs e 2 GB de swap.
Todos os comandos foram rodados em `~/genresearch`, com o venv ativado.

## Preparação
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Parte A: ambiente
```bash
bash scripts/env_report.sh        # gera results/env.txt
```

## Corpus e índices
```bash
python src/gen_corpus.py --size-mb 10   --out data/corpus_10mb.txt
python src/gen_corpus.py --size-mb 100  --out data/corpus_100mb.txt
python src/gen_corpus.py --size-mb 1000 --out data/corpus_1000mb.txt
python src/gen_corpus.py --size-mb 2500 --out data/corpus_2500mb.txt
python src/ingest.py --corpus data/corpus_10mb.txt   --index-dir data/index_10mb
python src/ingest.py --corpus data/corpus_100mb.txt  --index-dir data/index_100mb   # 3 repetições
python src/ingest.py --corpus data/corpus_1000mb.txt --index-dir data/index_1000mb
python src/ingest.py --corpus data/corpus_2500mb.txt --index-dir data/index_2500mb
```
Resultados: `results/raw/ingest.csv`.

## C1 e C2 (leitura convencional x mmap)
```bash
bash scripts/run_c1_c2.sh         # [ajuste para o comando e o arquivo de saída que você usou]
```

## C3 e C4 (concorrência e cache)
```bash
bash scripts/run_c3_c4.sh         # results/raw/c3.csv e results/raw/c4.csv
```

## C5 (pressão de memória)
```bash
bash scripts/run_c5.sh            # results/raw/c5.csv e results/vmstat_c5_*.txt
```

## C6 (falhas controladas)
```bash
bash scripts/run_c6.sh            # results/raw/c6.csv e results/logs/c6_saidas.txt
```

## Tabelas e gráficos
```bash
python scripts/summarize.py
python scripts/summarize_extra.py
python scripts/plots.py
```

## Data e commit de cada bateria

| Bateria | Resultados brutos | Data e hora | Commit |
|---|---|---|---|
| Ingestão 10 MB | results/raw/ingest.csv | 2026-10-20 20:08 | a204ce2 |
| Ingestão 100 MB (3 execuções) | results/raw/ingest.csv | 2026-10-20 20:16 a 20:20 | 26f399f |
| Ingestão 1.000 MB | results/raw/ingest.csv | 2026-10-20 21:16 | 83b7870 |
| Ingestão 2.500 MB | results/raw/ingest.csv | 2026-10-20 21:23 | 83b7870 |
| C1 e C2 | [arquivo] | [data] | [commit] |
| C3 | results/raw/c3.csv | [data] | [commit] |
| C4 | results/raw/c4.csv | [data] | [commit] |
| C5 | results/raw/c5.csv | [data] | [commit] |
| C6 | results/raw/c6.csv | [data] | [commit] |

Cada linha dos CSVs também guarda data e hora, commit e todos os parâmetros da execução.