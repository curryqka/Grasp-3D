# stage-1/stage-2 评测快照 — 2026-11-12

首个 E1 新机制链端到端评测证据批次（11-13 结论里程碑输入）。

## stage-1 主线 run_1030（keypoint，dla_34，20ep，seed317）完结 val

test split = val_scene1 695 帧（未现场景），平均 focal/ct loss，
keypoint_det.py --test（11-12 补丁路径，.orig 备份，训练路径零接触）：

| ckpt | val loss (focal/ct) | 说明 |
|---|---|---|
| model_best（epoch-end val 选出） | **2.3277** | 泛化峰值点 |
| model_last（ep20） | **3.0032** | 尾段回撤 29% |

未现场景泛化差距显著（训练末段 batch loss 0.3-0.5）；尾段过拟合回撤与
GraspSAM lr1e-4 线"峰值在中段"形态同构。

## stage-2 四线 30ep 终测（depth_width_angle_reg.py --test，model_last=ep30）

695 帧 / 22,240 抓取；depth/width 单位 mm，angle 单位 deg。

| 线 | seed | depth MAE | depth RMSE | width MAE | width RMSE | angle MAE |
|---|---|---|---|---|---|---|
| r2 | 317 | 153.0 | 187.5 | 15.9 | 21.5 | 19.37 |
| r3 | 717 | 154.5 | 185.2 | 15.6 | 20.7 | 20.20 |
| r4 | 1117 | 156.7 | 189.4 | 15.7 | 21.2 | 19.40 |
| r5 | 2117 | 149.5 | 186.2 | 15.5 | 20.3 | 19.88 |
| **mean（n=4 全种子）** | | **153.4** | **187.1** | **15.7** | **20.9** | **19.71** |

种子间离散（n=4）：depth MAE ±2.6 / width ±0.2 / angle ±0.35°——**stage-2 四种子
复制稳定性定案**（11-12 07:5x r3 终测收官，07:5x 批推送）。
width MAE ep1 冒烟 ~2m 异常已收案（BN running-stats 未收敛；30ep 后 15.5-15.9mm 与
训练 L1 量级吻合，观察点关闭）。

## 评测链工程记录

两处作者契约断裂同款补丁：stage-2 depth_width_angle_reg.py（11-10：val 返回值误解包 +
save_result 空壳 + run_eval 缺失三补丁）、stage-1 keypoint_det.py（11-12：val 旧签名 +
preds 误解包；hammer keypoint 数据集无 run_eval，按 11-08 已知跳过，产出=平均损失字典）。
均 .orig 备份、py_compile 通过、训练路径零接触，详见台账
Experiment/s2_closedloop/process_registry.md。
