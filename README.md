# Grasp-3D

A research algorithm library for robotic grasping — adapted implementations
of planar and 6-DoF grasp detection methods, with shared dataset adapters,
training loops, evaluation protocols and visualization tooling.

## Status

Early scaffold. The first entries (a planar grasping baseline adapted from
GraspSAM, and an RGB-only 6-DoF baseline) are being brought up and verified;
see [docs/ROADMAP.md](docs/ROADMAP.md) for the planned sequence and
[conventions](docs/ROADMAP.md#conventions).

## Layout

```
src/grasp3d/     library code (one subpackage per method + shared utils)
docs/            roadmap and per-entry notes
```

Datasets, pretrained weights, checkpoints and experiment outputs are kept
outside the repository; committed configs document how to reproduce them.

## License

Apache-2.0 — see [LICENSE](LICENSE). Adapted upstream methods keep their
own licenses and are credited in their entry READMEs.
