#!/usr/bin/env bash
# Coleta o ambiente de execucao (Parte A). Uso: bash scripts/env_report.sh
cd "$(dirname "$0")/.." || exit 1
[ -f .venv/bin/activate ] && source .venv/bin/activate
mkdir -p results

{
  echo "=== DATA ==="; date -Is
  echo "=== COMMIT ==="; git rev-parse HEAD
  echo "--- alteracoes nao commitadas (vazio = limpo) ---"; git status --short
  echo "=== KERNEL ==="; uname -a; uname -r
  echo "=== WSL ==="; grep -i microsoft /proc/version
  echo "=== OS ==="; cat /etc/os-release
  echo "=== CPU ==="; lscpu; echo "nproc: $(nproc)"
  echo "=== MEMORIA ==="; free -h; cat /proc/meminfo
  echo "=== SWAP ==="; swapon --show
  echo "=== DISCO ==="; lsblk; df -hT .
  echo "=== PYTHON ==="; which python3; python3 --version; pip freeze
  echo "=== GIT ==="; git --version
  echo "=== GPU ==="
  if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi; else echo "nenhuma detectada (nvidia-smi ausente) / nao utilizada"; fi

  echo "=== WINDOWS (host) ==="
  cmd.exe /c ver 2>/dev/null | tr -d '\r'
  wsl.exe --version 2>/dev/null | tr -d '\0\r'
  echo "=== .wslconfig ==="
  WINHOME=$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')" 2>/dev/null)
  cat "$WINHOME/.wslconfig" 2>/dev/null || echo ".wslconfig nao encontrado"

  echo "=== VMSTAT (repouso, 5 amostras) ==="; vmstat 1 5
  echo "=== IOSTAT (repouso, 5 amostras) ==="
  if command -v iostat >/dev/null 2>&1; then iostat -xz 1 5; else echo "iostat ausente (sudo apt install sysstat)"; fi
} > results/env.txt 2>&1

echo "gerado: results/env.txt"