#!/usr/bin/env python3
"""Allocation count for FilterChain.apply on a large offline torrent list.

Re-execs itself under PYTHONMALLOC=malloc and LD_PRELOAD of alloccount.c so
every object allocation is a malloc. Prints one integer: malloc/calloc/realloc
calls while iterating TorrentFilter('active|!complete'), the default first tab.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _ensure_hook():
    if os.environ.get("STIG_INTAKE_ALLOC_HOOK") == "1":
        return
    source = HERE / "alloccount.c"
    binary = Path("/tmp") / "stig-intake-alloccount.so"
    if (not binary.exists()) or binary.stat().st_mtime < source.stat().st_mtime:
        compiler = None
        for candidate in ("cc", "gcc"):
            if subprocess.call(["sh", "-c", f"command -v {candidate}"], stdout=subprocess.DEVNULL) == 0:
                compiler = candidate
                break
        if compiler is None:
            raise SystemExit("cc or gcc is required to build osspr-intake/harness/alloccount.c")
        subprocess.check_call(
            [compiler, "-shared", "-fPIC", "-O2", "-o", str(binary), str(source), "-ldl"]
        )
    env = os.environ.copy()
    env["STIG_INTAKE_ALLOC_HOOK"] = "1"
    env["PYTHONMALLOC"] = "malloc"
    preload = str(binary)
    if env.get("LD_PRELOAD"):
        preload = preload + ":" + env["LD_PRELOAD"]
    env["LD_PRELOAD"] = preload
    os.execvpe(sys.executable, [sys.executable, str(Path(__file__).resolve())], env)


def main():
    _ensure_hook()
    import ctypes
    import gc

    from stig.client.filters.torrent import TorrentFilter
    from stig.client.utils import Status

    statuses = (
        (Status.SEED, Status.IDLE),
        (Status.STOPPED,),
        (Status.CONNECTED, Status.DOWNLOAD),
        (Status.VERIFY,),
        (Status.UPLOAD, Status.SEED),
        (Status.IDLE,),
    )
    downloaded = (0, 12.5, 50, 99.2, 100, 100)
    torrents = [
        {
            "id": i,
            "name": f"ubuntu-{i}.iso" if i % 5 else f"linux-iso-{i}",
            "status": statuses[i % 6],
            "%downloaded": downloaded[i % 6],
        }
        for i in range(16000)
    ]
    filt = TorrentFilter("active|!complete")

    def apply_once():
        matched = 0
        for _item in filt.apply(torrents):
            matched += 1
        return matched

    expected = apply_once()
    lib = ctypes.CDLL(None)
    lib.stig_alloc_count.restype = ctypes.c_uint64
    lib.stig_alloc_reset.restype = None
    gc.collect()
    gc.disable()
    lib.stig_alloc_reset()
    matched = apply_once()
    count = int(lib.stig_alloc_count())
    gc.enable()
    if matched != expected:
        raise SystemExit(f"filter output changed: {matched} != {expected}")
    sys.stdout.write(f"{count}\n")


if __name__ == "__main__":
    main()
