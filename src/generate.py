"""Resposta simulada: custo de CPU proporcional ao contexto + espera de E/S simulada."""
import hashlib, time


def generate(query, ctx, cpu_per_kb=20000, io_ms=20.0):
    text = " ".join(ctx)
    x = 12345
    for _ in range(int(cpu_per_kb * len(text) / 1024)):   # CPU em Python puro (segura o GIL)
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
    if io_ms > 0:
        time.sleep(io_ms / 1000.0)                        # simula chamada a servico externo
    tag = hashlib.sha1((query + text).encode()).hexdigest()[:8]
    resumo = ctx[0][:60] if ctx else "(sem contexto)"
    return f"[{tag}] {len(ctx)} trechos: {resumo}..."