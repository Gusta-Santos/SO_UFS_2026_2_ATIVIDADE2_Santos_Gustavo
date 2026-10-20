"""Leitura de arquivos: convencional (read) e mapeada (mmap)."""
import mmap, os, random, resource, time, psutil

CHUNK = 1024 * 1024  # 1 MiB
PAGE = 4096

def snapshot():
    p = psutil.Process()
    mi = p.memory_info()
    ru = resource.getrusage(resource.RUSAGE_SELF)
    io = p.io_counters()
    return {"rss": mi.rss, "vms": mi.vms,
            "minflt": ru.ru_minflt, "majflt": ru.ru_majflt,
            "maxrss": ru.ru_maxrss * 1024,          # Linux: KiB -> bytes
            "io_read_bytes": io.read_bytes,         # bytes realmente vindos do disco
            "io_rchar": io.read_chars}              # bytes pedidos via syscalls

def meminfo():
    d = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":")
            d[k] = int(v.split()[0]) * 1024
    return d

def read_conventional(path, pattern="seq", n_random=2000, seed=1):
    """Retorna (bytes_lidos, t_abertura, t_leitura, snapshot_com_arquivo_aberto)."""
    total = 0
    t0 = time.perf_counter()
    f = open(path, "rb", buffering=0)
    t_open = time.perf_counter() - t0
    try:
        size = os.fstat(f.fileno()).st_size
        buf = bytearray(CHUNK)
        small = bytearray(PAGE)
        t1 = time.perf_counter()
        if pattern == "seq":
            while True:
                n = f.readinto(buf)
                if not n:
                    break
                total += n
        else:
            rnd = random.Random(seed)
            for _ in range(n_random):
                f.seek(rnd.randrange(0, max(1, size - PAGE)))
                total += f.readinto(small)
        t_read = time.perf_counter() - t1
        snap = snapshot()          # arquivo ainda aberto
    finally:
        f.close()
    return total, t_open, t_read, snap

def read_mmap(path, pattern="seq", n_random=2000, seed=1):
    """Mesmo trabalho (copia para buffer pre-alocado), mas via mmap."""
    total = 0
    t0 = time.perf_counter()
    f = open(path, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    t_open = time.perf_counter() - t0
    buf = bytearray(CHUNK)
    bmv = memoryview(buf)
    try:
        size = len(mm)
        t1 = time.perf_counter()
        with memoryview(mm) as mv:
            if pattern == "seq":
                for off in range(0, size, CHUNK):
                    n = min(CHUNK, size - off)
                    bmv[:n] = mv[off:off + n]
                    total += n
            else:
                rnd = random.Random(seed)
                for _ in range(n_random):
                    off = rnd.randrange(0, max(1, size - PAGE))
                    n = min(PAGE, size - off)
                    bmv[:n] = mv[off:off + n]
                    total += n
        t_read = time.perf_counter() - t1
        snap = snapshot()          # arquivo ainda mapeado
    finally:
        bmv.release()
        mm.close()
        f.close()
    return total, t_open, t_read, snap
