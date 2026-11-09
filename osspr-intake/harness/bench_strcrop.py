#!/usr/bin/env python3
"""Wall time for stig.utils.string.strcrop on a large torrent-name list.

Prints one sample in milliseconds. The workload is offline: clip long release
names to column widths the way the TUI crops tab titles.
"""
import gc
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stig.utils.string import strcrop

WIDTHS = (24, 40, 64, 80)
TAIL = "…"


def build_names():
    names = []
    wide = "映画ダウンロード日本語タイトル "
    episode = "進撃の巨人 "
    for i in range(8000):
        if i % 5 == 0:
            names.append(f"{wide}{i} " + episode * 6 + "1080p BluRay")
        else:
            names.append(
                f"Ubuntu.Server.{i}.amd64.iso." + "extra-long-release-name-" * 8
            )
    return names


NAMES = build_names()


def once():
    total = 0
    crop = strcrop
    tail = TAIL
    for name in NAMES:
        for width in WIDTHS:
            total += len(crop(name, width, tail=tail))
    return total


# One pass is a few hundred milliseconds and a single scheduling stall moves it
# by several percent. Repeat a fixed number of passes so the sample is the same
# work every run and short stalls are a small fraction of the total.
PASSES = 4


def _timed_passes():
    gc.collect()
    gc.disable()
    started = time.perf_counter()
    got = 0
    for _ in range(PASSES):
        got += once()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    gc.enable()
    return got, elapsed_ms


def main():
    expected = once()
    once()
    # Drop the first timed loop. A fresh process pays an allocator/CPU ramp
    # that is not part of the steady cost of strcrop.
    _timed_passes()
    got, elapsed_ms = _timed_passes()
    if got != expected * PASSES:
        raise SystemExit(f"strcrop output changed: {got} != {expected * PASSES}")
    sys.stdout.write(f"{elapsed_ms:.4f}\n")


if __name__ == "__main__":
    main()
