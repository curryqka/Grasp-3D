#!/usr/bin/env python3
"""Group official Jacquard files into the two-level layout GraspSAM expects.

Official Jacquard extracts to root/<scene>/<sid>_*; GraspSAM's JacquardDataset
glob expects root/<scene>/<sid>/<sid>_*. This script hardlinks ONLY the
samples whose ids appear in the official split pickles
(split/jacquard/{seen,unseen}.obj) into the ready layout. Idempotent: skips
already-linked files.

Usage:
    JACQUARD_EXTRACTED=<dir> JACQUARD_READY=<dir> JACQUARD_SPLIT_DIR=<dir> \
        python jacq_group_split.py
"""
import os
import pickle
import sys

EXTRACTED = os.environ.get("JACQUARD_EXTRACTED", "./jacquard_extracted")
READY = os.environ.get("JACQUARD_READY", "./jacquard_ready")
SPLIT_DIR = os.environ.get("JACQUARD_SPLIT_DIR", "./split/jacquard")
SUFFIXES = ("_RGB.png", "_mask.png", "_grasps.txt")

ids = set()
for s in ("seen", "unseen"):
    with open(os.path.join(SPLIT_DIR, s + ".obj"), "rb") as f:
        ids.update(pickle.load(f))
print(f"split ids: {len(ids)}", flush=True)

ok = miss = linked = skipped = 0
for sid in sorted(ids):
    scene = sid.split("_", 1)[1]
    src_dir = os.path.join(EXTRACTED, scene)
    dst_dir = os.path.join(READY, scene, sid)
    os.makedirs(dst_dir, exist_ok=True)
    good = True
    for suf in SUFFIXES:
        src = os.path.join(src_dir, sid + suf)
        dst = os.path.join(dst_dir, sid + suf)
        if os.path.exists(dst):
            skipped += 1
            continue
        if not os.path.exists(src):
            print(f"MISS {sid+suf}", flush=True)
            good = False
            continue
        try:
            os.link(src, dst)
        except OSError:
            import shutil
            shutil.copyfile(src, dst)
        linked += 1
    ok += good
    if not good:
        miss += 1

print(f"READY_GROUP_DONE ids={len(ids)} complete={ok} incomplete={miss} "
      f"linked={linked} skipped_existing={skipped}", flush=True)
