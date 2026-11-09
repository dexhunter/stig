#!/usr/bin/env python3
"""Wall time for DataSizeConverter.__call__ on plain byte counts.

SizeInBytes and BandwidthInBytes both go through this function when a torrent
cache entry is rebuilt. Prints one sample in milliseconds.
"""
import gc
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stig.utils import convert

# One row stands in for size-final / size-downloaded / size-uploaded /
# rate-down / rate-up on a poll where those raw integers changed.
VALUES = tuple(i * 4096 for i in range(30000))


def once():
    size = convert.size
    bandwidth = convert.bandwidth
    last = None
    for value in VALUES:
        last = size(value, unit="byte")
        last = bandwidth(value, unit="byte")
    return int(last)


PASSES = 6


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
    # The first timed loop in a fresh process is slower (allocator / CPU ramp).
    # Discard it and report the following loop, which is the steady rate.
    _timed_passes()
    got, elapsed_ms = _timed_passes()
    if got != expected * PASSES:
        raise SystemExit(f"datasize output changed: {got} != {expected * PASSES}")
    sys.stdout.write(f"{elapsed_ms:.4f}\n")


if __name__ == "__main__":
    main()
