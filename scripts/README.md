# Utility scripts

Companion tooling developed while reproducing the GraspSAM baseline
(see `../docs/patches/PATCHES.md` and `../docs/baselines/`). All scripts are
path-agnostic — pass locations as arguments or environment variables; no
machine-specific paths are hardcoded.

## Data download & preparation

| Script | Purpose |
|---|---|
| `par_download.sh <url> <out> [nparts]` | Parallel ranged downloader: N concurrent curl range requests, per-part resume, exact-size verification before concatenation. Works for any HTTP source exposing `Content-Length`. |
| `chain_housecat6d.sh [dest]` | Serial download of the six HouseCat6D volumes (TUM CAMP) with a free-disk watchdog (aborts below 150 GB) and skip-if-complete. |
| `chain_hammer.sh [dest]` | Single-zip HAMMER dataset download with the same watchdog pattern. |
| `jacquard_chain.sh [dest]` | Jacquard 12-volume download + **official MD5 verification** per volume (table from the CNRS download page; fetch it separately — it is public). Credentials, if needed, go in `~/.netrc` (picked up by `curl --netrc`); never in the script. |
| `hammer_extract.py` | Parallel zip extraction (thread pool, idempotent by size, disk watchdog). Configure `HAMMER_ROOT`/`HAMMER_OUT` env vars and the `ZIPS` list. |
| `jacq_group_split.py` | Re-groups official Jacquard files into the two-level `<scene>/<sid>/` layout GraspSAM's glob expects, hardlinking only samples in the official seen/unseen split pickles. |

## Evaluation

| Script | Purpose |
|---|---|
| `quick_eval.py` | Fast probe: first N unseen samples with the exact official metric (IoU>0.25, angle≤30°). Run from a patched GraspSAM checkout; pass `--ckp` and `--root`. ~100 samples ≈ 3 min on one GPU, vs ~43 min for the full 4198-sample eval. |
| `eval_watcher.sh` | Unattended evaluation: polls for epoch checkpoints, runs the official `eval.py` full-pool eval on a given GPU, auto-appends final accuracy to a markdown tracking table. Lets baseline numbers accumulate while training runs unattended. |

## Conventions used across the download scripts

1. **Resume everything**: completed files (exact byte size / MD5) are skipped;
   partial ranged parts resume from their current size.
2. **Watchdogs abort, never delete**: on low disk the scripts exit with a
   distinct code and log line (`ABORT_*`) rather than removing data.
3. **Verify before trust**: Jacquard is checked against official MD5s;
   everything else against exact byte length from `Content-Length`.

## Example

```bash
# Jacquard: 12 volumes (~60 GB), MD5-verified, resumable
./jacquard_chain.sh ./jacquard
# then extract and group into the GraspSAM layout
python hammer_extract.py     # after editing ZIPS, or see script
JACQUARD_EXTRACTED=./jacquard_extracted JACQUARD_READY=./jacquard_ready \
JACQUARD_SPLIT_DIR=<GraspSAM>/split/jacquard python jacq_group_split.py

# evaluate a checkpoint on a subset, then set up the full-eval watcher
python quick_eval.py --ckp runs/<run>/epoch39.pth --root ./grasp_anything --n 100
GRASPSAM_LOCAL=<GraspSAM> PYTHON_BIN=python BASELINE_TABLE=baselines.md \
  ./eval_watcher.sh runs/<run> 39,59,79 grasp_anything ./grasp_anything 0 myrun myrun
```
