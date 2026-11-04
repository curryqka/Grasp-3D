# Baseline tracking snapshot — 2026-11-04

Reproduction of the GraspSAM (ICRA 2025) planar grasp baseline with the
official training and evaluation pipeline, after applying the `crop_size=1024`
fixes described in [`docs/patches/PATCHES.md`](../patches/PATCHES.md).

## Protocol

- Model: `PlanarGraspSAM` (`bs_grasp_sam`), SAM encoder `vit_t`, `num_layers=0`
- Training: official recipe — AdamW lr 1e-5, batch 4, 200 epochs,
  CosineAnnealingLR(T_max=20, eta_min=1e-7) restarting every 20 epochs
- Evaluation: official `eval.py`, full unseen pool, batch size 1, deterministic
  (no augmentation, eval mode). Metric: grasp success rate (IoU-style
  rectangle match as implemented upstream)
- Pools: Grasp-Anything unseen (4198 samples), Jacquard unseen (374 samples)
- Hardware: 1× RTX A5000 (24 GB) per training run; ~43 min per full GA eval

## Results (official full-pool eval)

### Grasp-Anything unseen (4198 samples)

| Run | ep19 | ep39 | ep49 (mid-cycle) | ep59 |
|---|---|---|---|---|
| run A (default init) | 65.82% | 65.82% | 65.32% | 64.91% |
| run B (seed 42) | — | 68.15% | 67.65% (ep32) | 67.20% |

### Jacquard unseen (374 samples)

| Run | ep0 | ep43 | ep59 |
|---|---|---|---|
| Jacquard baseline | 42.51% | 57.49% | 61.76% |

## Observations (preliminary, training ongoing)

1. **Plateau with periodic-restart jitter.** Run A's cycle-tail accuracy is
   65.82% → 65.82% → 64.91% across Cosine restart cycles — the 20-epoch
   restarts converge to essentially the same solution from ep19 on. Mid-cycle
   checkpoints (ep49) score slightly lower than cycle tails, consistent with
   the restart schedule.
2. **Seed variance exceeds residual training gains.** With an identical
   protocol, the seed-42 run sits **+2.3 pt above the default-init run at both
   ep39 and ep59** (a stable offset, not noise). A multi-seed mean±std is
   required for any baseline claim; two more seeds are training.
3. **Jacquard climbs without plateau** through ep59 (+19 pt over ep0).
4. Both runs drop ~0.9 pt from ep39 to ep59 in parallel — a systematic
   cycle-3 effect worth tracking, not seed noise.
5. Early evaluation order matters: mid-eval running accuracy on GA can swing
   several points before converging (samples are not difficulty-shuffled);
   only full-pool finals are comparable.

## Reproduction index

- Upstream code: gist-ailab/GraspSAM, checkout dated 2026-11-02
- Local patches: see [`docs/patches/`](../patches/)
- Datasets: Grasp-Anything (official), Jacquard v1.1 (official, MD5-verified)
- Full running table lives in the project workspace; this file is a dated
  snapshot and is not updated in place.
