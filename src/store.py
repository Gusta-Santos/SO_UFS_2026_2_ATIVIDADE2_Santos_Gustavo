"""Leitura de arquivos: convencional (read) e mapeada (mmap)."""
import mmap, os, random, resource, psutil

CHUNK = 1024 * 1024  # 1 MiB

def snapshot():
    p = psutil.Process()
    mi = p.memory_info()
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return {"rss": mi.rss, "vms": mi.vms,
            "minflt": ru.ru_minflt, "majflt": ru.ru_majflt}

def meminfo():
    d = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":")
            d[k] = int(v.split()[0]) * 1024
    return d

def read_conventional(path, pattern="seq", n_random=2000, seed=1):
    """open()+read(). 'seq' le tudo em blocos; 'rand' faz leituras aleatorias."""
    total = 0
    with open(path, "rb", buffering=0) as f:
        size = os.fstat(f.fileno()).st_size
        if pattern == "seq":
            while True:
                b = f.read(CHUNK)
                if not b:
                    break
                total += len(b)
        else:
            rnd = random.Random(seed)
            for _ in range(n_random):
                f.seek(rnd.randrange(0, max(1, size - 4096)))
                total += len(f.read(4096))
    return total

def read_mmap(path, pattern="seq", n_random=2000, seed=1):
    """mmap. 'seq' percorre em blocos; 'rand' acessa offsets aleatorios."""
    total = 0
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            if pattern == "seq":
                for off in range(0, size, CHUNK):
                    total += len(mm[off:off + CHUNK])
            else:
                rnd = random.Random(seed)
                for _ in range(n_random):
                    off = rnd.randrange(0, max(1, size - 4096))
                    total += len(mm[off:off + 4096])
    return total
