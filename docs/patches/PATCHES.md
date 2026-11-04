# GraspSAM upstream patches applied in this project

Upstream: [gist-ailab/GraspSAM](https://github.com/gist-ailab/GraspSAM) (ICRA 2025).
These patches were developed while reproducing the official training/evaluation
pipeline in November 2025. All six changes are minimal and are recorded as
unified diffs against the upstream checkout.

## The `crop_size=224` trap (patches T1 / E2)

`GraspAnythingDataset` has a **default `crop_size=224`**, while the rest of the
pipeline is built around 1024×1024:

- grasp rectangles are normalized against the network output size and drawn in
  the 1024-space;
- `post_process_output` unconditionally interpolates predictions to 1024².

The upstream `train.py` and `eval.py` **Grasp-Anything branches construct the
dataset without passing `crop_size`**, so ground-truth grasp maps are drawn in a
224-space while predictions live in a 1024-space.

### Symptom

With an under-trained or even reasonably trained model, the official
`eval.py` on Grasp-Anything reports **0.00% grasp success**: predicted and
ground-truth grasp pixels barely overlap (cross-space IoU ≈ 0), and during
training the grasp-quality head collapses to an all-zero local optimum because
the rendered GT maps are almost empty.

The Jacquard branch is unaffected — it already passes `crop_size=1024`
explicitly — which makes the GA-only failure easy to misattribute to training
issues. We diagnosed it by probing the GT quality-map statistics
(`q_gt.max = 0` with `crop_size=224` vs. 20k–80k non-zero pixels with 1024).

### Fix

Pass `crop_size=1024` explicitly in both GA dataset constructions:

- `graspsam_train_crop_size.patch` — training branch (T1)
- `graspsam_eval_crop_size.patch` — evaluation branch (E2)

**Rule of thumb: any new caller of `GraspAnythingDataset` must pass
`crop_size=1024` explicitly.**

## Other changes

| ID | File | Change | Why |
|---|---|---|---|
| T2 | train.py | add `--seed` argument and seed `random`/`numpy`/`torch` before training | multi-seed variance estimation (upstream has no seed control) |
| E1 | eval.py | `PlanarGraspSAM(..., num_layers=0)` | match the trained model config (`num_layers=0`); upstream default builds a different decoder stack, so trained checkpoints load inconsistently |
| E3 | eval.py | build the model with `sam_encoder_type="vit_t"` instead of hardcoded `"eff_vit_t_w_ad"` | evaluate the checkpoint actually trained; also avoids the upstream `pretrained_checkpoints` (plural) path bug in the eff branch |
| E4 | eval.py | normalize `didx` to a Python int | batch-size-1 tensors arrive as 0-dim tensors and break indexing downstream |

## Verification

After applying the patches and training from scratch with the official recipe
(vit_t encoder, `bs_grasp_sam`, AdamW lr 1e-5, batch 4, CosineAnnealingLR
period 20), the official full-pool unseen evaluation (4198 Grasp-Anything
samples, batch size 1) went from **0.00%** (before patches, under-trained) to
**>65%** at epoch 19 and beyond. See `docs/baselines/` for the running
baseline table snapshot.

## Applying

```bash
cd <GraspSAM checkout>
patch -p2 --dry-run < graspsam_train_crop_size.patch   # adjust -p level to your layout
patch -p2 --dry-run < graspsam_eval_crop_size.patch
```

The diffs were produced from the upstream files as of 2026-11-02; line numbers
may drift on newer upstream commits.
