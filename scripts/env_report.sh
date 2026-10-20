#!/bin/bash
mkdir -p results
{
  echo "=== DATA ==="; date
  echo "=== KERNEL ==="; uname -a
  echo "=== WSL ==="; grep -i microsoft /proc/version
  echo "=== OS ==="; cat /etc/os-release
  echo "=== CPU ==="; lscpu
  echo "=== MEMORIA ==="; free -h; head -30 /proc/meminfo
  echo "=== SWAP ==="; swapon --show
  echo "=== DISCO ==="; lsblk; df -h ~
  echo "=== FS DO PROJETO ==="; df -T ~/genresearch
  echo "=== PYTHON ==="; python3 --version; pip freeze
  echo "=== GPU ==="; echo "nenhuma / nao utilizada"
  echo "=== COMMIT ==="; git rev-parse HEAD
} > results/env.txt 2>&1
echo "gerado: results/env.txt"
