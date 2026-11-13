"""PoseMatch@K evaluator for the HouseCat6D->HAMMER converted 6D grasp data.

Protocol: v5 references/04_evaluation_protocol.md section 7 (PM-2026-11-13-v1).
Conventions (skill grasp-6d-eval section 1):
  - camera frame, z = optical axis, right-handed; positions/widths in meters,
    rotations in radians internally.
  - per-frame grasps in HouseCat6D grasps/polarization/<frame>.h5 are ALREADY
    in that frame's camera frame (verified by the converter, which projects
    grasp_points directly with K). The per-scene grasps_info_base.h5 is a
    concatenation of those camera-frame grasps; visible-H5 grasp_index rows
    address it. So no per-frame object pose is needed on the GT side.
  - contact center c = midpoint of the two contact points; native gripper
    origin t_nat = c - 0.11217 * R[:,2] (approach axis = 3rd column,
    closing axis = 1st column). The reference-point audit stats emitted by
    load_scene() are the empirical G1 input.
  - gripper symmetry set S = {I, Rz(pi)} (180 deg about the approach axis:
    finger swap). Nothing else is assumed.

Self-checks (skill section 3) must all pass before any 6D number is recorded.
"""
from __future__ import annotations
import argparse, glob, json, math, os, sys
import numpy as np
import h5py

PROTOCOL = "PM-2026-11-13-v1"
TIP_OFFSET = 0.11217          # native gripper origin <-> contact center
SYMS = (np.eye(3), np.array([[-1.0, 0, 0], [0, -1.0, 0], [0, 0, 1.0]]))
TAU_T, TAU_R, TAU_W = 0.03, math.radians(30.0), 0.02


# ----------------------------------------------------------------- geometry
def rot_angle(R: np.ndarray) -> float:
    return float(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)))


def dR_sym(Rp: np.ndarray, Rg: np.ndarray) -> float:
    return min(rot_angle(Rp.T @ Rg @ s) for s in SYMS)


def match(Rp, tp, wp, Rg, tg, wg, tt=TAU_T, tR=TAU_R, tw=TAU_W) -> bool:
    """All three thresholds must hold for the SAME (prediction, GT) pair.

    Thresholds are inclusive per protocol; the +1e-9 guard keeps float
    perturbations exactly ON the boundary (e.g. w+0.02) inside."""
    if not np.all(np.isfinite(tp)) or not np.all(np.isfinite(Rp)):
        return False
    if float(np.linalg.norm(tp - tg)) > tt + 1e-9:
        return False
    if dR_sym(Rp, Rg) > tR + 1e-9:
        return False
    return abs(float(wp) - float(wg)) <= tw + 1e-9


# ----------------------------------------------------------------- GT load
def load_scene(scene_dir: str, max_frames: int = 0):
    """GT grasps per (frame, obj) + reference-point audit stats.

    Returns (gt, audit) where
      gt[frame_stem][obj] = [(R, t_nat, w, grasp_id), ...]   (camera frame)
      audit = ndarray (n,3): ||T_t - t_nat||, ||T_t - c||, dot(c - t_nat, a)
    """
    dump_p = os.path.join(scene_dir, "grasps_info_base.h5")
    dumps = {}
    with h5py.File(dump_p, "r") as f:
        for obj in f:
            if f[obj]["grasp_points"].shape[0]:
                dumps[obj] = (np.array(f[obj]["transforms"]),
                              np.array(f[obj]["grasp_points"]))
    frames = sorted(glob.glob(os.path.join(
        scene_dir, "grasps_visible_hard", "polarization", "*.h5")))
    if max_frames:
        frames = frames[:max_frames]
    gt, audit = {}, []
    for fp in frames:
        stem = os.path.basename(fp)[:-3]
        with h5py.File(fp, "r") as f:
            for obj in f:
                m = np.array(f[obj]["match_pixel_grasp"])
                if not len(m):
                    continue
                T, gp = dumps[obj]
                lst = []
                for u, v, gi, _c4 in m:
                    gi = int(gi)
                    if gi >= T.shape[0]:
                        continue
                    R = T[gi, :3, :3]
                    p0, p1 = gp[gi, 0], gp[gi, 1]
                    c = (p0 + p1) / 2.0
                    t_nat = c - TIP_OFFSET * R[:, 2]
                    w = float(np.linalg.norm(p0 - p1))
                    lst.append((R, t_nat, w, gi))
                    tt = T[gi, :3, 3]
                    audit.append((np.linalg.norm(tt - t_nat),
                                  np.linalg.norm(tt - c),
                                  float(np.dot(c - t_nat, R[:, 2]))))
                if lst:
                    gt.setdefault(stem, {})[obj] = lst
    return gt, (np.array(audit) if audit else np.zeros((0, 3)))


# ----------------------------------------------------------------- metric
def pose_match(gt_scene, preds_scene, K=1, tt=TAU_T, tR=TAU_R, tw=TAU_W):
    """Macro-average over eligible observations.

    preds_scene[frame][obj] = [(R, t, w), ...] sorted by score DESC (the
    caller owns NMS; this evaluator consumes the ranked list as-is).
    Returns (rate, n_eligible, hits) with hits[(frame,obj)] in {0,1}.
    """
    hits, n = {}, 0
    for frame, objs in gt_scene.items():
        for obj, gts in objs.items():
            n += 1
            preds = preds_scene.get(frame, {}).get(obj, [])[:K]
            hit = 0
            for (Rp, tp, wp) in preds:
                if any(match(Rp, tp, wp, Rg, tg, wg, tt, tR, tw)
                       for (Rg, tg, wg, _gi) in gts):
                    hit = 1
                    break
            hits[(frame, obj)] = hit
    return (sum(hits.values()) / n if n else 0.0), n, hits


# ------------------------------------------------------------- self-checks
def _unit(rng):
    v = rng.normal(size=3)
    return v / np.linalg.norm(v)


def _rot(axis, ang):
    k = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


def run_selfchecks(scene_dir, out_dir, max_frames=0):
    rng = np.random.default_rng(0)
    gt, audit = load_scene(scene_dir, max_frames)
    # one-GT-per-obs synthetic subset for perturbation checks: with ~200 GTs
    # per observation a perturbed grasp can legitimately match a NEIGHBOR GT,
    # masking the threshold behaviour the checks verify. We keep the FIRST GT
    # of each observation as its only GT inside the check scene.
    gt_single = {fr: {ob: gts[:1] for ob, gts in objs.items()}
                 for fr, objs in gt.items()}
    rep = {"protocol": PROTOCOL, "scene": scene_dir,
           "n_eligible_obs": sum(len(o) for o in gt.values()),
           "n_single_gt_obs": sum(len(o) for o in gt_single.values()),
           "checks": {}}

    def scene_preds(gt_scene, transform):
        """build a prediction scene by transforming every GT grasp"""
        out = {}
        for fr, objs in gt_scene.items():
            for ob, gts in objs.items():
                out.setdefault(fr, {})[ob] = [
                    transform(Rg, tg, wg, gi) for (Rg, tg, wg, gi) in gts]
        return out

    def at1(gt_scene, preds, **kw):
        r, n, _ = pose_match(gt_scene, preds, K=1, **kw)
        return r, n

    # 1 GT self-match -> 100%
    r1, n1 = at1(gt, scene_preds(gt, lambda R, t, w, gi: (R, t, w)))
    rep["checks"]["gt_self_match"] = {"rate": r1, "expect": 1.0,
                                      "pass": r1 == 1.0}
    # 2 empty predictions -> 0%
    r2, _ = at1(gt, {})
    rep["checks"]["empty_predictions"] = {"rate": r2, "expect": 0.0,
                                          "pass": r2 == 0.0}
    # 3 wrong object in same frame -> ~0%
    wrong = {}
    for fr in sorted(gt.keys()):
        objs = gt[fr]
        keys = sorted(objs.keys())
        if len(keys) < 2:
            continue
        shifted = {keys[i]: objs[keys[i - 1]] for i in range(len(keys))}
        wrong[fr] = {ob: [(R, t, w) for (R, t, w, _g) in gts]
                     for ob, gts in shifted.items()}
    r3, n3 = at1(gt, wrong)
    rep["checks"]["wrong_object"] = {"rate": r3, "expect_lt": 0.02,
                                     "pass": r3 < 0.02}
    # 4 translation perturbation 1/2/3/5 cm on single-GT obs
    chk4 = {}
    for cm in (1, 2, 3, 5):
        d = cm / 100.0
        r4, _ = at1(gt_single, scene_preds(
            gt_single, lambda R, t, w, gi, d=d: (R, t + d * _unit(rng), w)))
        chk4[f"{cm}cm"] = r4
    rep["checks"]["translation_perturb"] = {
        "rates": chk4, "expect": "1-3cm high, 5cm ~0",
        "pass": chk4["1cm"] > 0.95 and chk4["3cm"] > 0.95
                and chk4["5cm"] < 0.05}
    # 5 rotation perturbation about closing axis on single-GT obs.
    # Magnitude sampled in (0.7a, a] so the 45deg draw is fully beyond the
    # 30deg threshold (uniform(-a,a) would put 2/3 of draws inside it).
    chk5 = {}
    for deg in (20, 30, 45):
        a = math.radians(deg)
        r5, _ = at1(gt_single, scene_preds(
            gt_single,
            lambda R, t, w, gi, a=a: (
                R @ _rot(R[:, 0], rng.uniform(a * 0.7, a) * rng.choice([-1, 1])),
                t, w)))
        chk5[f"{deg}deg"] = r5
    rep["checks"]["rotation_perturb"] = {
        "rates": chk5, "expect": "20/30deg high, 45deg ~0",
        "pass": chk5["20deg"] > 0.95 and chk5["30deg"] > 0.95
                and chk5["45deg"] < 0.05}
    # 6 approach-axis 180 deg symmetry -> hit
    r6, _ = at1(gt, scene_preds(gt, lambda R, t, w, gi: (R @ SYMS[1], t, w)))
    rep["checks"]["symmetry_swap_fingers"] = {"rate": r6, "expect": 1.0,
                                              "pass": r6 == 1.0}
    # 7 width perturbation +1/2/3 cm on single-GT obs
    chk7 = {}
    for cm in (1, 2, 3):
        d = cm / 100.0
        r7, _ = at1(gt_single, scene_preds(
            gt_single, lambda R, t, w, gi, d=d: (R, t, w + d)))
        chk7[f"{cm}cm"] = r7
    rep["checks"]["width_perturb"] = {
        "rates": chk7, "expect": "1-2cm high, 3cm ~0",
        "pass": chk7["1cm"] > 0.95 and chk7["2cm"] > 0.95
                and chk7["3cm"] < 0.05}
    # 8 origin mixing: pass contact center as t_nat -> collapse
    r8, _ = at1(gt, scene_preds(
        gt, lambda R, t, w, gi: (R, t + TIP_OFFSET * R[:, 2], w)))
    rep["checks"]["origin_mixing"] = {
        "rate": r8, "expect_lt": 0.05,
        "pass": r8 < 0.05,
        "note": "t_nat + 0.11217*a = contact center passed as origin"}

    # reference-point audit (G1 input)
    if len(audit):
        rep["reference_audit"] = {
            "n": int(len(audit)),
            "median_|T_t-t_nat|_m": float(np.median(audit[:, 0])),
            "mean_|T_t-t_nat|_m": float(np.mean(audit[:, 0])),
            "median_|T_t-c|_m": float(np.median(audit[:, 1])),
            "median_dot(c-t_nat,a)_m": float(np.median(audit[:, 2])),
            "frac_dot_gt_0": float(np.mean(audit[:, 2] > 0)),
        }
    rep["all_pass"] = all(
        v.get("pass", True) for v in rep["checks"].values())

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "selfcheck_report.json"), "w") as f:
        json.dump(rep, f, indent=1)
    lines = [f"PoseMatch self-check — {PROTOCOL} — {scene_dir}",
             f"eligible observations: {rep['n_eligible_obs']}"]
    for k, v in rep["checks"].items():
        val = v.get("rate", v.get("rates"))
        lines.append(f"  [{'PASS' if v['pass'] else 'FAIL'}] {k}: {val}")
    if "reference_audit" in rep:
        ra = rep["reference_audit"]
        lines += [
            f"  reference audit (n={ra['n']}):",
            f"    median |T_t - t_nat| = {ra['median_|T_t-t_nat|_m']*1000:.1f} mm",
            f"    median |T_t - c|     = {ra['median_|T_t-c|_m']*1000:.1f} mm",
            f"    median dot(c-t_nat, a) = {ra['median_dot(c-t_nat,a)_m']*1000:.1f} mm"
            f"  (frac>0: {ra['frac_dot_gt_0']:.3f})"]
    lines.append(f"ALL {'PASS' if rep['all_pass'] else 'FAIL'}")
    txt = "\n".join(lines)
    with open(os.path.join(out_dir, "selfcheck_report.txt"), "w") as f:
        f.write(txt + "\n")
    print(txt)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--max-frames", type=int, default=0)
    a = ap.parse_args()
    rep = run_selfchecks(a.scene_dir, a.out_dir, a.max_frames)
    sys.exit(0 if rep["all_pass"] else 1)


if __name__ == "__main__":
    main()
