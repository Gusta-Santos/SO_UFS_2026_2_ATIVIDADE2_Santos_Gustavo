"""Gera corpus sintetico de texto (sem dados reais) em tamanho alvo."""
import argparse, random, os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size-mb", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    rnd = random.Random(a.seed)
    vocab = [f"termo{i}" for i in range(5000)]
    target = int(a.size_mb * 1024 * 1024)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    written = 0
    doc = 0
    with open(a.out, "w", encoding="utf-8") as f:
        while written < target:
            n = rnd.randint(80, 200)
            line = f"[doc{doc}] " + " ".join(rnd.choices(vocab, k=n)) + "\n"
            f.write(line)
            written += len(line.encode("utf-8"))
            doc += 1
    print(f"{a.out}: {written/1024/1024:.1f} MB, {doc} documentos")

if __name__ == "__main__":
    main()
