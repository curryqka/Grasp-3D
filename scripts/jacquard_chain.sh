#!/bin/bash
# Jacquard 12-volume download + official md5sum verification.
# Usage: jacquard_chain.sh [DEST_DIR]
#
# Requires the official MD5 table (public, from the Jacquard download page
# https://jacquard.liris.cnrs.fr/files/database/download.php) as a text file;
# set JACQUARD_MD5_TABLE or place jacquard_md5.txt in DEST_DIR. Each volume is
# verified against the official hash immediately after download and removed on
# mismatch; already-verified volumes are skipped on re-run.
#
# Jacquard requires credentials: put them in ~/.netrc for the host
# jacquard.liris.cnrs.fr — par_download.sh picks them up via curl --netrc.
# Never store credentials in this script or its arguments.
#
# Env: PAR_DOWNLOAD       path to par_download.sh (default: next to this script)
#     JACQUARD_MD5_TABLE  path to the official md5 table
set -u
JQ=${1:-./jacquard}
PAR=${PAR_DOWNLOAD:-$(dirname "$0")/par_download.sh}
MD5TAB=${JACQUARD_MD5_TABLE:-$JQ/jacquard_md5.txt}
MIN_FREE_BYTES=$((150 * 1024 * 1024 * 1024))
BASE=https://jacquard.liris.cnrs.fr/data/Download
LOGSTAMP() { date '+%F %T'; }

dfcheck() {
    avail=$(df --output=avail -B1 "$JQ" 2>/dev/null | tail -1)
    if [ "${avail:-0}" -lt "$MIN_FREE_BYTES" ]; then
        echo "ABORT_DISK_LOW $(LOGSTAMP) avail=${avail}"; exit 42
    fi
}

official_md5() {
    awk -v n="$1" '$0 ~ "Jacquard_Dataset_" n "\\.zip" {print $2; exit}' "$MD5TAB"
}

mkdir -p "$JQ"
for n in $(seq 0 11); do
    f="Jacquard_Dataset_${n}.zip"
    want=$(official_md5 "$n")
    if [ -z "$want" ]; then echo "ABORT_NO_MD5 vol=$n"; exit 45; fi

    dfcheck
    if [ -f "$JQ/$f" ] && echo "$(md5sum "$JQ/$f" 2>/dev/null | awk '{print $1}') $JQ/$f" \
       | grep -q "^$want"; then
        echo "SKIP_MD5_OK $(LOGSTAMP) $f"
        continue
    fi
    # stale/mismatched file: remove before redownload
    rm -f "$JQ/$f" "$JQ/$f".part*

    echo "START $(LOGSTAMP) $f"
    bash "$PAR" "$BASE/$f" "$JQ/$f" 8
    rc=$?
    sz=$(stat -c%s "$JQ/$f" 2>/dev/null || echo 0)
    echo "END $(LOGSTAMP) $f rc=$rc size=$sz"
    if [ $rc -ne 0 ] || [ "$sz" -le 1000000 ]; then
        echo "ABORT_JQ $(LOGSTAMP) vol=$n"; exit 41
    fi

    echo "VERIFY_MD5 $(LOGSTAMP) $f"
    got=$(md5sum "$JQ/$f" | awk '{print $1}')
    if [ "$got" = "$want" ]; then
        echo "MD5_OK $(LOGSTAMP) $f"
    else
        echo "MD5_FAIL $(LOGSTAMP) $f got=$got want=$want"; rm -f "$JQ/$f"; exit 44
    fi
done
echo "JACQUARD_ALL_DONE $(LOGSTAMP)"
