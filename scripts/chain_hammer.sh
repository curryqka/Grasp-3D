#!/bin/bash
# HAMMER dataset download chain (single large zip). Partial-part resumable.
# Usage: chain_hammer.sh [DEST_DIR]
#
# Checks free space on the destination filesystem before downloading and
# aborts below the threshold.
#
# Env: PAR_DOWNLOAD  path to par_download.sh (default: next to this script)
set -u
HAMMER=${1:-./hammer}
PAR=${PAR_DOWNLOAD:-$(dirname "$0")/par_download.sh}
MIN_FREE_BYTES=$((150 * 1024 * 1024 * 1024))
LOGSTAMP() { date '+%F %T'; }

mkdir -p "$HAMMER"
avail=$(df --output=avail -B1 "$HAMMER" 2>/dev/null | tail -1)
if [ "${avail:-0}" -lt "$MIN_FREE_BYTES" ]; then
    echo "ABORT_DISK_LOW $(LOGSTAMP) avail=${avail}"; exit 42
fi

echo "START $(LOGSTAMP) HAMMER/_dataset_processed.zip"
bash "$PAR" https://www.campar.in.tum.de/public_datasets/2022_arxiv_jung/_dataset_processed.zip \
    "$HAMMER/_dataset_processed.zip" 8
rc=$?
echo "END $(LOGSTAMP) HAMMER rc=$rc size=$(stat -c%s "$HAMMER/_dataset_processed.zip" 2>/dev/null || echo 0)"
[ $rc -ne 0 ] && { echo "ABORT_HAMMER $(LOGSTAMP)"; exit 43; }
echo "ALL_DONE $(LOGSTAMP)"
