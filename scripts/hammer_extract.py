#!/usr/bin/env python3
"""Parallel zip extractor with a disk-space watchdog.

Extracts one or more zips into OUT, writing files with a thread pool (latency
bound on network filesystems), skipping files that already exist with the
matching size (idempotent / resumable), and aborting when the destination
filesystem drops below MIN_FREE_BYTES.

Usage: HAMMER_ROOT=<zip dir> HAMMER_OUT=<out dir> python hammer_extract.py
Edit `ZIPS` below for the archive names to extract.
"""
import os
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.environ.get("HAMMER_ROOT", "./hammer")
OUT = os.environ.get("HAMMER_OUT", os.path.join(ROOT, "extracted"))
ZIPS = ["_dataset_processed.zip"]
N_WORKERS = 48
MIN_FREE_BYTES = 150 * 1024 * 1024 * 1024
SKIP_SUFFIX = ()

read_lock = threading.Lock()


def dfcheck():
    mount = OUT if os.path.exists(OUT) else (os.path.dirname(os.path.abspath(OUT)) or ".")
    st = os.statvfs(mount)
    avail = st.f_bavail * st.f_frsize
    if avail < MIN_FREE_BYTES:
        print(f"ABORT_DISK_LOW avail={avail}", flush=True)
        sys.exit(42)


def extract_zip(zip_path):
    dfcheck()
    t0 = time.time()
    z = zipfile.ZipFile(zip_path)
    tasks = []
    for info in z.infolist():
        if info.is_dir():
            continue
        base = os.path.basename(info.filename)
        if not base or base.endswith(SKIP_SUFFIX) or "__MACOSX" in info.filename:
            continue
        dst = os.path.join(OUT, info.filename)
        if os.path.exists(dst) and os.path.getsize(dst) == info.file_size:
            continue
        tasks.append((info, dst))
    print(f"{os.path.basename(zip_path)}: {len(tasks)} files to extract", flush=True)
    if not tasks:
        z.close()
        return

    counters = {"done": 0, "fail": 0}
    dirs_seen = set()

    def work(args):
        info, dst = args
        try:
            d = os.path.dirname(dst)
            if d not in dirs_seen:
                os.makedirs(d, exist_ok=True)
                dirs_seen.add(d)
            with read_lock:
                with z.open(info) as src:
                    data = src.read()
            tmp = dst + ".tmp"
            with open(tmp, "wb") as out:
                out.write(data)
            os.replace(tmp, dst)
            counters["done"] += 1
            if counters["done"] % 2000 == 0:
                rate = counters["done"] / max(time.time() - t0, 1)
                print(f"  {counters['done']}/{len(tasks)} {rate:.1f} files/s", flush=True)
        except Exception as e:
            counters["fail"] += 1
            print(f"FAIL {info.filename}: {e}", flush=True)

    with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
        list(ex.map(work, tasks))
    print(f"{os.path.basename(zip_path)} DONE: extracted={counters['done']} "
          f"fail={counters['fail']} elapsed={time.time()-t0:.0f}s", flush=True)
    z.close()


def main():
    print(f"zips: {ZIPS}", flush=True)
    for f in ZIPS:
        extract_zip(os.path.join(ROOT, f))
    print("EXTRACT_ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
