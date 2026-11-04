#!/bin/bash
# Serial multi-volume download chain with a per-volume disk-space watchdog.
# Usage: chain_housecat6d.sh [DEST_DIR]
#
# Downloads the six HouseCat6D volumes (TUM CAMP public dataset) one at a time
# via par_download.sh (8 parallel ranged parts, resumable). Before each volume
# it checks free space on the destination filesystem and aborts below the
# threshold; completed volumes (exact byte match) are skipped on re-run.
#
# Env: PAR_DOWNLOAD  path to par_download.sh (default: next to this script)
DEST=${1:-./housecat6d}
PAR=${PAR_DOWNLOAD:-$(dirname "$0")/par_download.sh}
BASE=https://www.campar.in.tum.de/public_datasets/2023_housecat6d_new
MIN_FREE_GB=150
mkdir -p "$DEST"
LOG=$DEST/download.log
for u in scene1-10 scene11-20 scene21-34 val_scene test_scene obj_models; do
  FREE=$(df --output=avail -BG "$DEST" | tail -1 | tr -dc '0-9')
  if [ "${FREE:-0}" -lt "$MIN_FREE_GB" ]; then echo "ABORT_ENOSPC free=${FREE}G $(date '+%F %T')" >> "$LOG"; exit 1; fi
  OUT=$DEST/$u.zip
  EXPECT=$(curl -sI "$BASE/$u.zip" | grep -i content-length | awk '{print $2}' | tr -d '\r')
  CUR=$(stat -c%s "$OUT" 2>/dev/null || echo 0)
  if [ -n "$EXPECT" ] && [ "$CUR" = "$EXPECT" ]; then echo "SKIP_DONE $u ($CUR bytes)" >> "$LOG"; continue; fi
  echo "START $u expect=$EXPECT $(date '+%F %T')" >> "$LOG"
  bash "$PAR" "$BASE/$u.zip" "$OUT" 8 >> "$LOG" 2>&1
  echo "END $u exit=$? size=$(stat -c%s "$OUT" 2>/dev/null) $(date '+%F %T')" >> "$LOG"
done
echo "HOUSECAT6D_ALL_DONE $(date '+%F %T')" >> "$LOG"
