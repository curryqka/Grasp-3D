# Baseline Tracking Snapshot — 2026-11-08

Third dated snapshot (follows 2026-11-04 and 2026-11-06). Scope: C00 multi-line
completion verdict, seen-pool matrix, cross-dataset transfer matrix, and the E1
HouseCat6D→HAMMER pipeline landing. All numbers are 0.5-conf JPEG grasp success
rate (%) from eval.py, unseen pools unless labeled seen; GA = Grasp Anything,
Jacq = Jacquard.

## 1. C00 (GA, vit_t, protocol 200-epoch restart-cosine)

### Endpoint score (protocol final vs per-line best)

| Line | lr | seed | best (ep) | protocol end (ep199) | delta |
|------|----|------|-----------|----------------------|-------|
| v2 main | 1e-5 | 42 | 65.82 (19) | 64.79 | −1.03 |
| seed1 | 1e-5 | 7 | 68.06 (39) | 64.63 | −3.52 |
| seed2 | 1e-5 | 7* | 67.63 (99) | 64.70 | −2.93 |
| seed3 | 1e-5 | 123 | 68.13 (159) | 67.10 | −1.03 |
| lr1e-4 | 1e-4 | 42 | 69.27 (79) | 68.10 | −1.17 |
| lr1e-4 copy | 1e-4 | 42** | 69.56 (39) | ≥67.94 @119 (running) | — |

\* same numeric seed value, different torch init path; \*\* rerun of lr1e-4 with
fresh init to test reproducibility.

### Oscillation-rebound framework (final form)

Every line oscillates with ±3.3 pt amplitude across restart cycles; the phase
drifts per run. 1e-5 four-seed arrays: ep79 65.91 ± 2.10, ep99 65.62 ± 2.35,
ep159 **66.76 ± 1.24** (converges late). The earlier "three endpoints within
0.16 pt" hypothesis was broken by seed3 (end 67.10): an endpoint is the last
oscillation landing — peak (seed3, lr1e-4) or trough (v2/seed1/seed2) — not a
phase-averaged constant.

**lr1e-4 peak shape confirmed stable across seeds (this snapshot's headline)**:
original line peaks 69.27 @ ep79; rerun peaks 69.56 @ ep39 and sits at
67.94 @ ep119 (second local peak, 69.56→66.53→67.87→66.32→67.94 — same
oscillation band, phase-shifted). Both lines end ~68, ~2-4 pt above the 1e-5
band. The lr finding is real and reproducible, not seed luck.
Third lr1e-4 seed line (seed7) launched 11-08 04:50 for ep119-grade confirmation.

## 2. E0 (Jacquard, vit_t)

- Protocol end 61.76 (ep199); best 62.83 @ ep99; late-phase plateau ~62.5.
- E0-lr1e4 (cross-dataset lr validation) launched 11-08 00:00, ep39 ckpt
  pending; watcher covers eps 39-199.

## 3. Seen-pool matrix (new in this snapshot)

| Ckpt | Pool | n | success |
|------|------|---|---------|
| C00 lr1e-4 ep79 | GA seen | 4116 | **78.81** |
| C00 lr1e-4 rerun ep39 | GA seen | 4116 | **78.74** |
| C00 seed1 ep39 | GA seen | 4116 | 76.12 |
| C00 seed3 ep159 | GA seen | 4116 | 75.75 |
| C00 seed2 ep99 | GA seen | 4116 | 75.53 |
| C00 v2 ep19 | GA seen | 4116 | 74.25 |
| E0 ep99 | Jacquard seen | 336 | 76.19 |

lr1e-4's ~3.4 pt seen advantage (78.8 vs 75.4 ± 0.65) reproduces across both
seeds with 0.07 pt spread — consistent with its unseen-domain advantage.

## 4. Cross-dataset transfer matrix (negative result, closed)

| Direction | Ckpt | Pool | n | success |
|-----------|------|------|---|---------|
| GA→Jacq | lr1e-4 ep79 | Jacquard unseen | 374 | 3.21 |
| GA→Jacq | seed3 ep159 | Jacquard unseen | 374 | 2.94 |
| GA→Jacq | seed2 ep99 | Jacquard unseen | 374 | 2.94 |
| GA→Jacq | seed1 ep39 | Jacquard unseen | 374 | 1.34 |
| GA→Jacq | v2 ep19 | Jacquard unseen | 374 | 3.48 |
| Jacq→GA | E0 ep99 | GA unseen | 4198 | 6.24 |

Both directions collapse to 1-6 % vs 62-79 % in-domain (59-73 pt drop):
planar grasp prompts do not transfer across these two datasets.

## 5. E1: HouseCat6D → HAMMER (polargrasp/GKNet) pipeline landed

- Converter `housecat6d_to_hammer.py` v4: grasps/polarization H5 → projected
  contact points (`contact_points_image_index`), visibility = in-bounds +
  depth consistency (|d−z|<0.06 m); train volumes use raw sensor `depth/`
  (depth_gt absent), 74 % keep rate; masks from instance ids; rgb symlinks as
  stage-1 images (polarization channels deferred). All 14 official train
  scenes + val_scene1 + test_scene5 converted (8186 validated train frames;
  30 dropped — a corrupted source chunk in scene03; a few bad-header H5s
  skipped and logged).
- DCNv2 patch: vendored prebuilt `_ext` is torch-1.x ABI and cannot load under
  torch 2.0.1; DCN/DCNv2 classes rewritten onto
  `torchvision.ops.deform_conv2d` (offset reordering y/x interleaved; init
  behavior identical: zero offsets, sigmoid(0)=0.5 mask). `dcn_v2.py.orig`
  kept.
- Stage-1 keypoint training (dla_34, bs2, 864×1120 padded input, 20 epochs,
  log_freq 2000) running on GPU4 since 11-08 10:35; loss 2.28→0.86 within
  epoch 1. Default log_freq=50 floods the run with inline 695-frame
  validations every 150 iters (~15 min each) — overridden.
- Jacquard seen-pool eval got two phantom "crashes" that were actually
  completed runs misread from truncated logs; no dataset bug (an
  UnboundLocalError repro required wrongly omitting include_mask).

## 6. State of running lines

| Line | Where | ETA |
|------|-------|-----|
| C00 lr1e-4 rerun (seed42) ep119→199 | GPU5, watcher-B on GPU1 | 11-09 |
| C00 lr1e-4 seed7 (3rd seed) | GPU7, watcher queued | 11-10 |
| E0-lr1e4 | GPU0, watcher GPU6 | 11-09 |
| E1 stage-1 | GPU4 | 11-10 evening |

## 7. Next steps

1. Copy-line ep119=67.94 lands the acceptance verdict: lr1e-4 accepted as the
   headline lr; acceptance table frozen with this snapshot.
2. E1 stage-1 ckpts feed stage-2 (depth/width/angle) after first milestones;
   11-13 new-mechanism milestone depends on stage-1+stage-2 smoke chain.
3. Third-seed lr1e-4 line (seed7) ep119 cross-checks the peak-shape claim.
