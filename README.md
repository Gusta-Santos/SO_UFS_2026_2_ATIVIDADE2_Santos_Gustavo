# GenResearch-Servidor

Serviço simplificado inspirado em IA generativa/RAG, usado para estudar como memória principal, memória virtual, armazenamento, caches, filas e sincronização afetam desempenho, estabilidade e correção.

- **Disciplina:** Sistemas Operacionais, UFS, Departamento de Computação (AV2, Atividade 2)
- **Aluno:** Gustavo Santos Oliveira (trabalho individual)
- **Professor:** Glauco de Figueiredo Carneiro
- **Vídeo (até 20 min):** [[PREENCHER URL](https://youtu.be/BvyIsx3JqeY)] (também em `VIDEO.md`)

> Declaração de uso de ferramentas de terceiros: o código dos scripts foi elaborado com auxílio de um assistente de IA (Claude, Anthropic) e revisado, executado e adaptado pelo autor.

## Pipeline

produtores → fila limitada → consumidores → cache compartilhado → recuperação → geração (simulada) → log

Os dados são **sintéticos** (semente fixa 42). Os vetores (128 dimensões, float32) e a geração são **simulados**; não há modelo, GPU, chaves, `.env` nem dados pessoais.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `src/gen_corpus.py` | gera o corpus sintético (tamanho em MB) |
| `src/ingest.py`, `src/vecstore.py` | ingestão, fragmentação e índice (SQLite + vetores binários) |
| `src/retrieve.py` | recuperação por similaridade de cosseno (mmap ou RAM) |
| `src/generate.py` | geração simulada (laço de CPU + espera de E/S) |
| `src/cache.py` | cache compartilhado (LRU/FIFO) com lock |
| `src/logger.py` | log de eventos com escrita protegida |
| `src/server.py` | fila, threads, métricas e experimentos C3 a C6 |
| `src/memtest.py` | leitura convencional vs mmap (C1/C2) |
| `src/demo_race.py` | Parte D: condição de corrida, correção e single-flight |
| `scripts/run_c1_c2.sh`, `run_c3_c4.sh`, `run_c5.sh` | baterias de experimentos |
| `results/raw/` | resultados brutos (CSV) |
| `results/logs/` | logs de eventos, `strace`, threads (`ps`, `top`) |
| `results/figures/` | gráficos e tabelas-resumo |
| `results/COMANDOS.md` | comandos na ordem de execução |

## Ambiente de referência

Windows 10 + WSL2 (Ubuntu 22.04.5), kernel 6.18.54.1-microsoft-standard-WSL2, limites do WSL: 4 GB de RAM, 4 CPUs, 2 GB de swap. Python 3.10.12 (numpy, pandas, matplotlib, psutil). Detalhes completos no relatório (Parte A).

## Como reproduzir

```bash
# 1. dependências
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. corpus e índice (os dados NÃO são versionados)
python src/gen_corpus.py --size-mb 100 --out data/corpus_100mb.txt
python src/ingest.py --help      # gera o índice em data/index_100mb

# 3. experimentos (WSL em repouso; alguns pedem sudo para drop_caches)
bash scripts/run_c1_c2.sh        # C1 e C2: read vs mmap
bash scripts/run_c3_c4.sh        # C3 (concorrência) e C4 (cache)
bash scripts/run_c5.sh           # C5: pressão de memória (índices de 100, 1000 e 2500 MB)
# C6: falhas controladas, ver results/COMANDOS.md

# 4. Parte D: sincronização
python src/demo_race.py --reps 3 --out results/raw/d_race.csv
strace -f -c -e trace=futex python src/demo_race.py --reps 1 --out /tmp/x.csv 2> results/logs/strace_futex.txt
```

Os corpora de 1.000 e 2.500 MB e seus índices ocupam vários GB; gere-os apenas se for rodar o C5 (ver `SIZES` em `scripts/run_c5.sh`). Todas as execuções gravam em `results/raw/` com data, hora, commit e parâmetros.

## Principais resultados

- **C5:** com índice maior que a RAM (6,48 GB), a recuperação saltou de ~96 ms para 1.181 ms, com 7.226 faltas major e 241 MB de swap.
- **C4:** com consultas repetidas e cache de 20 ou mais entradas, taxa de acerto de 0,94 e vazão ~15× maior.
- **C3:** speedup de 3,83 (cenário io) e 2,15 (cenário cpu) com 4 consumidores.
- **Parte D:** sem proteção, ~73% das atualizações foram perdidas, 60 de 80 cálculos duplicados e 67 a 121 de 1.200 linhas de log corrompidas; mutex e single-flight os eliminaram.

Análise completa no relatório em PDF.

## Limitações

Vetores e geração simulados, sem GPU, busca por varredura completa, ambiente WSL2 de nó único e threads limitadas pelo GIL. Os resultados não se generalizam para modelos maiores, múltiplas GPUs ou ambientes distribuídos.