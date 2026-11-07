# Baseline snapshot — 2026-11-06

Second dated snapshot of the GraspSAM reproduction (first: 2026-11-04).
Protocol unchanged: `PlanarGraspSAM(vit_t, num_layers=0)`, official 200-epoch
schedule (AdamW, CosineAnnealingLR restarted every 20 epochs), batch size 4 in
training / 1 in evaluation, official `eval.py` on the full unseen pools
(Grasp-Anything unseen n=4198, Jacquard unseen n=374). Both crop_size patches
from `docs/patches/` are applied to every run. Numbers are full-pool final
values only (mid-eval running accuracy is noisy and never compared).

Training is still running at snapshot time (ETA 2026-11-07); lines marked
(ongoing) will get a final snapshot on completion.

## Grasp-Anything unseen (n=4198) — full-pool accuracy per checkpoint

| run | init | lr | ep19 | ep39 | ep59 | ep79 | ep99 | ep119 | ep139 | ep159 | ep179 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v2 | unseeded A | 1e-5 | 65.82 | 65.82 | 64.91 | 63.63 | 62.24 | 62.84 | 62.46 | 65.67 | 62.72 |
| seed1 | seed 42 | 1e-5 | — | 68.15 | 67.20 | 68.06 | 66.63 | 67.15 | 64.70 | 65.75 | (ongoing) |
| seed2 | seed 7 | 1e-5 | — | — | — | 67.27 | 67.63 | 67.15 | (ongoing) | | |
| seed3 | seed 123 | 1e-5 | — | — | — | 64.67 | 65.96 | 67.10 | (ongoing) | | |
| lr1e-4 | unseeded B | 1e-4 | — | 65.51 | 66.82 | 69.27 | 66.51 | 63.17 | 66.72 | (ongoing) | |

Also: v2 ep49 = 65.32 (mid-period), seed1 ep32 = 67.65 (seed-variance first
point). A fifth line (lr1e-4 + seed 42) is training to test whether the lr
1e-4 peak is init-dependent.

### 4-seed arrays (official lr 1e-5 only)

| epoch | v2 | seed1 | seed2 | seed3 | mean ± std (n−1) |
|---|---|---|---|---|---|
| 79 | 63.63 | 68.06 | 67.27 | 64.67 | **65.91 ± 2.10** (range 4.39) |
| 99 | 62.24 | 66.63 | 67.63 | 65.96 | **65.62 ± 2.35** |
| 119 | 65.67 | 65.75 | 67.15 | 67.10 | **66.42 ± 0.82** |

## Jacquard unseen (n=374) — E0, training complete

| ep0 | ep43 | ep59 | ep99 | ep139 | ep179 | ep199 (final) |
|---|---|---|---|---|---|---|
| 42.51 | 57.49 | 61.76 | 62.83 | 62.57 | 61.50 | **61.76** |

Best checkpoint 62.83 @ ep99. Curve: fast climb to a ~62.5 plateau by ep59,
then a mild late drift (−1 to −1.3 pt) mirroring the late-phase wobble seen on
the GA lr 1e-5 lines.

## Observations (supersedes the 2026-11-04 list)

1. **Oscillation–rebound, not monotone decay.** Every long-running line swings
   by up to ±3.3 pt across the 20-epoch restart periods, with dip/rebound
   phases at different epochs per run: v2 dipped over ep79–139 (62.2–63.6)
   then rebounded to 65.67 @ ep159 before dipping again (62.72 @ ep179);
   lr1e-4 went 69.27 → 63.17 → 66.72; seed1 dipped to 64.70 @ ep139 and was
   recovering at ep159. seed2/seed3 had shown no dip through ep119.
   An intermediate reading of this data as "late overfitting per seed" was
   rejected once the rebounds landed.
2. **Seed variance dominates the plateau.** 4-seed spread at ep79 is 4.39 pt
   (±2.10); it exceeds any epoch-to-epoch gain past ep39. The unseeded-init
   run (v2) is the low outlier early on but rejoins the pack at ep159.
3. **Best checkpoints are always mid-training.** Per-line best so far: v2
   65.82 @ ep19/39, seed1 68.15 @ ep39, seed2 67.63 @ ep99, seed3 67.10 @
   ep119 (still climbing), lr1e-4 69.27 @ ep79, Jacquard 62.83 @ ep99. The
   official 200-epoch endpoint is never the best point in our reproduction;
   early stopping (or per-period evaluation) would gain 2–6 pt.
4. **lr 1e-4 vs 1e-5: no systematic plateau difference.** An early reading
   ("1e-4 only converges faster"), then a mid-run one ("1e-4 climbs higher"),
   both gave way to: same plateau level, same late oscillation, phase shifted.
5. **Mid-eval running accuracy is not interpretable.** GA eval samples are
   shuffled by dataset order, not difficulty; running accuracy swings several
   points mid-eval. Only full-pool final values are compared (this bit us
   once; see the 2026-11-04 snapshot, obs. 5).

## Provenance

- Runs live under `runs/<name>/seen_vit_t_default/grasp_anything/<timestamp>/`
  on the experiment host; every number above is appended automatically by
  `scripts/eval_watcher.sh` from official `eval.py` output.
- Patches required for these numbers: `docs/patches/graspsam_train_crop_size.patch`,
  `docs/patches/graspsam_eval_crop_size.patch` (0% → 65%+ without them).
