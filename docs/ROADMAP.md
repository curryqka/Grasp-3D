# Roadmap

Coarse plan for building up this library. Items move to "Done" only
after their training/evaluation path has been verified end to end.

## In progress

- **Library skeleton** — package layout, coding conventions, docs.

## Planned

1. **Planar grasping baseline (GraspSAM adaptation)**
   SAM-prompt-conditioned planar grasp detection (ICRA 2025, gist-ailab),
   adapted for local training and evaluation on standard planar benchmarks
   (Jacquard, Grasp-Anything). Includes dataset adapters and the official
   evaluation protocol.
2. **RGB-only 6-DoF grasping baseline (HAMMER line)**
   Monocular RGB 6-DoF grasping, including conversion utilities for the
   grasp-annotation formats used by this line of work.
3. **Shared evaluation & visualization tooling**
   Common metrics, result tables, and grasp rendering used across entries.
4. **Method development**
   New ideas built on top of the reproduced baselines; added once a
   reproducible gain over a baseline is measured.

## Conventions

- Code lives under `src/grasp3d/`; large data, weights and checkpoints
  stay outside the repository.
- Each adapted method keeps a pointer to its upstream source and license.
- Experiments are reproducible via committed configs; results snapshots
  are documented alongside the code that produced them.

## License

Apache-2.0. Upstream sources adapted into this library keep their own
licenses and are credited in their entry READMEs.
