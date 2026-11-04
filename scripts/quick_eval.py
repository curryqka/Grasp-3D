"""Quick unseen-split evaluation probe: first N samples, IoU>0.25 & angle<=30deg metric.
Usage: python quick_eval.py --ckp <path.pth> [--n 100] [--gpu 0] [--root <dataset dir>]
Mirrors eval.py's metric exactly (post_process_output + detect_grasps + GraspRectangles).

Run from the (patched) GraspSAM checkout root — imports its data/model/eval
modules. The dataset root can be given via --root or the GRASP_ANYTHING_ROOT
env var.
"""
import os, argparse, warnings
warnings.filterwarnings(action='ignore')
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"

import numpy as np
import torch

from data.grasp_anything_data import GraspAnythingDataset
from model.planar_grasp_sam import PlanarGraspSAM
from eval import post_process_output
from data.utils.grasp_utils import detect_grasps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckp", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--root", default=os.environ.get("GRASP_ANYTHING_ROOT"),
                    help="Grasp-Anything prepared dataset root (or set GRASP_ANYTHING_ROOT)")
    ap.add_argument("--seen", action="store_true", help="probe seen train split instead of unseen")
    args = ap.parse_args()
    if not args.root:
        ap.error("--root is required (or set GRASP_ANYTHING_ROOT)")

    # NOTE: crop_size=1024 must be explicit — the upstream default is 224, which
    # mis-renders GT grasps (see docs/patches/PATCHES.md).
    ds = GraspAnythingDataset(root=args.root, crop_size=1024,
                              seen=args.seen, train=False, include_mask=True,
                              random_rotate=False, random_zoom=False)
    n = min(args.n, len(ds))

    model = PlanarGraspSAM(sam_encoder_type='vit_t', num_layers=0)
    dev = torch.device(f'cuda:{args.gpu}' if torch.cuda.is_available() else 'cpu')
    model = model.to(dev)
    sd = torch.load(args.ckp, map_location='cpu')
    if "module." in list(sd["model"].keys())[0]:
        sd = {k[7:]: v for k, v in sd.items()}
    model.load_state_dict(sd["model"], strict=False)
    model.eval()

    correct = 0
    with torch.no_grad():
        for didx in range(n):
            x, mask, grasps, idx, rot, zoom = ds[didx]
            tg = {'masks': mask.unsqueeze(0).to(dev),
                  'grasps': [g.unsqueeze(0).to(dev) for g in grasps]}
            gp, mp = model.total_forward(imgs=x.unsqueeze(0).to(dev), targets=tg)
            p = model.compute_loss(gp, mp, tg, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0)['pred']
            q_out, ang_out, w_out = post_process_output(
                p['pos'].cpu(), p['cos'].cpu(), p['sin'].cpu(), p['width'].cpu())
            gt = ds.get_gtbb(int(idx), rot, zoom)
            det = detect_grasps(q_out, ang_out, width_img=w_out, no_grasps=1)
            ok = any(g.max_iou(gt) > 0.25 for g in det)
            correct += int(ok)
            if (didx + 1) % 10 == 0:
                print(f"{didx+1}/{n}  acc={100*correct/(didx+1):.2f}%  q.max={q_out.max():.4f}", flush=True)
    print(f"QUICK_EVAL_DONE ckp={os.path.basename(os.path.dirname(args.ckp))} "
          f"n={n} acc={100*correct/n:.2f}% ({correct}/{n})", flush=True)


if __name__ == "__main__":
    main()
