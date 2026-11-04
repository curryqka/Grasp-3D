#!/bin/bash
# usage: eval_watcher.sh <CKPT_DIR> <EP_LIST_CSV> <DATASET_NAME> <ROOT> <GPU> <PREFIX> <TAG>
#
# Unattended evaluation loop: waits (5-min poll) for each epoch checkpoint to
# appear, runs the official eval.py on the given GPU, then appends the final
# full-pool success rate to the baseline tracking table. Lets evaluation
# results trickle in automatically while training runs.
#
# Env:
#   GRASPSAM_LOCAL   patched GraspSAM checkout (run dir; default: .)
#   PYTHON_BIN       python interpreter (default: python)
#   BASELINE_TABLE   markdown table to append results to (default: ./baseline_tracking.md)
GRASPSAM_LOCAL=${GRASPSAM_LOCAL:-.}
PYTHON_BIN=${PYTHON_BIN:-python}
BASELINE_TABLE=${BASELINE_TABLE:-./baseline_tracking.md}
CKPT_DIR=$1; EPS=$2; DNAME=$3; ROOT=$4; GPU=$5; PREFIX=$6; TAG=$7
LOCAL=$GRASPSAM_LOCAL
POOL="GA unseen"; [ "$DNAME" = "jacquard" ] && POOL="Jacquard unseen"
for EP in ${EPS//,/ }; do
  until CKPT=$(ls "$CKPT_DIR/epoch${EP}.pth" 2>/dev/null); do sleep 300; done
  LOG="$LOCAL/${PREFIX}_ep${EP}_eval.log"
  echo "EVAL_START ckpt=$CKPT $(date '+%F %T')" >> "$LOG"
  cd "$LOCAL" || exit 1
  CUDA_VISIBLE_DEVICES=$GPU "$PYTHON_BIN" -u eval.py --dataset_name "$DNAME" --root "$ROOT" \
    --ckp_path "$CKPT" --gpu-num 0 --batch-size 1 >> "$LOG" 2>&1
  echo "EVAL_DONE $(date '+%F %T')" >> "$LOG"
  LAST=$(grep "success rate" "$LOG" | tail -1)
  ACC=$(echo "$LAST" | sed 's/success rate : \([0-9.]*\)%.*/\1/')
  C=$(echo "$LAST" | sed 's/.*correct : \([0-9]*\).*/\1/')
  F=$(echo "$LAST" | sed 's/.*failed : \([0-9]*\).*/\1/')
  echo "| $(date '+%m-%d %H:%M') | $TAG epoch$EP (auto) | \`$(basename $(dirname $CKPT))\` | $POOL | $((${C}+${F})) (${C}/${F}) | **${ACC}%** |" >> "$BASELINE_TABLE"
  echo "BASELINE_APPENDED $TAG epoch$EP acc=${ACC}%" >> "$LOG"
done
echo "WATCHER_ALL_DONE $TAG $(date '+%F %T')" >> "$LOCAL/${PREFIX}_watcher.log"
