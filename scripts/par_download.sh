#!/bin/bash
# Parallel ranged downloader: N concurrent curl range requests, per-part resume.
# Usage: par_download.sh <url> <output_file> [nparts]
#
# - Splits the file into NP byte ranges fetched by concurrent curls.
# - Each part is resumed independently (partial part appends the remaining
#   range), so an interrupted download loses at most one part of progress.
# - Verifies every part size against the expected range, concatenates in
#   order, and removes the parts only if the final size matches exactly.
#
# `--netrc` is used so credential-protected sources read ~/.netrc if present;
# it is a no-op for anonymous downloads.
set -u
URL=$1; OUT=$2; NP=${3:-8}

sz=$(curl -sIL --netrc "$URL" | grep -i '^content-length' | tail -1 | tr -dc '0-9')
if [ -z "$sz" ] || [ "$sz" -le 0 ]; then echo "PAR_ERR no content-length"; exit 2; fi

# final size marker: if OUT already complete, skip
if [ -f "$OUT" ] && [ "$(stat -c%s "$OUT")" -eq "$sz" ]; then echo "PAR_SKIP complete"; exit 0; fi

chunk=$(( (sz + NP - 1) / NP ))
pids=()
for ((i=0; i<NP; i++)); do
    start=$(( i * chunk ))
    end=$(( start + chunk - 1 )); [ "$end" -ge "$sz" ] && end=$(( sz - 1 ))
    [ "$start" -ge "$sz" ] && break
    want=$(( end - start + 1 ))
    part=$(printf "%s.part%02d" "$OUT" "$i")
    have=$(stat -c%s "$part" 2>/dev/null || echo 0)
    if [ "$have" -eq "$want" ]; then continue; fi
    if [ "$have" -gt 0 ] && [ "$have" -lt "$want" ]; then
        # partial part: append remaining range (resumable within part)
        ( curl -s --netrc --retry 30 --retry-delay 5 --retry-all-errors --max-time 0 \
              -r "$((start+have))-$end" -o - "$URL" >> "$part" ) &
    else
        rm -f "$part"
        ( curl -s --netrc --retry 30 --retry-delay 5 --retry-all-errors --max-time 0 \
              -r "$start-$end" -o "$part" "$URL" ) &
    fi
    pids+=($!)
done
rc=0
for p in "${pids[@]:-}"; do [ -n "$p" ] && wait "$p" || rc=1; done

# verify all parts
total=0
for ((i=0; i<NP; i++)); do
    start=$(( i * chunk )); [ "$start" -ge "$sz" ] && break
    end=$(( start + chunk - 1 )); [ "$end" -ge "$sz" ] && end=$(( sz - 1 ))
    want=$(( end - start + 1 ))
    part=$(printf "%s.part%02d" "$OUT" "$i")
    have=$(stat -c%s "$part" 2>/dev/null || echo 0)
    if [ "$have" -ne "$want" ]; then echo "PAR_ERR part$i have=$have want=$want"; exit 3; fi
    total=$(( total + have ))
done

# concat parts in order
> "$OUT"
for ((i=0; i<NP; i++)); do
    part=$(printf "%s.part%02d" "$OUT" "$i")
    [ -f "$part" ] && cat "$part" >> "$OUT"
done
final=$(stat -c%s "$OUT")
if [ "$final" -eq "$sz" ]; then
    rm -f "$OUT".part*
    echo "PAR_OK $OUT size=$final"
else
    echo "PAR_ERR concat final=$final expect=$sz"
    exit 4
fi
