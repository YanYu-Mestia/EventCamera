# DHP19 第一组数据：20 帧验证教程

本文说明如何在 WSL Ubuntu 中复现 DHP19 `S1/session1/mov1` 的前 20 个事件帧，并检查事件数据与 Vicon 姿态标注是否正确对齐。

这一步是正式批量预处理前的小样本验证，不是训练数据生成，也不需要 OpenEB、物理事件相机或 Windows Python 环境。

## 1. 已验证的输入

默认使用以下文件：

```text
事件数据  D:\DHP19\DVS_movies\S1\session1\mov1.aedat
Vicon 标注 D:\DHP19\Vicon_data\S1_1_1.mat
投影矩阵  D:\DHP19\P_matrices\P1.npy 至 P4.npy
项目代码  D:\EventPoseFinal
输出目录  D:\DHP19_preprocessed\verification\S1_session1_mov1_20frames
```

程序只读取 `D:\DHP19` 中的原始文件，结果写到 `D:\DHP19_preprocessed`。重复运行时使用临时文件完成后再替换已有结果，避免留下只写了一部分的 HDF5、JSON 或 PNG 文件。

## 2. 创建或更新独立环境

打开 WSL Ubuntu，运行：

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/setup_dhp19_environment.sh
```

脚本会创建或更新 Conda 环境 `eventpose-dhp19`，环境定义保存在：

```text
D:\EventPoseFinal\environment\wsl\dhp19-environment.yml
```

本次验证使用的主要版本是 Python 3.12、NumPy 2.1、SciPy 1.15、h5py 3.13、Matplotlib 3.10、Numba 0.61 和 pytest 8.3。这个环境只负责 DHP19 解析和验证，不要把 OpenEB 的 Windows DLL 或未来的 MMPose 训练依赖混入其中。

## 3. 运行第一组 20 帧验证

在 WSL Ubuntu 中运行：

```bash
cd /mnt/d/EventPoseFinal
/home/mestia/miniconda3/bin/conda run --no-capture-output \
  -n eventpose-dhp19 \
  python scripts/data/process_dhp19_sample.py
```

成功时会依次显示 `labels`、`aedat`、`filter`、`write` 阶段，最后显示：

```text
result=ok frames=20 output=/mnt/d/DHP19_preprocessed/verification/S1_session1_mov1_20frames
```

需要处理其他样本或调整帧数时，可显式传入参数：

```bash
python scripts/data/process_dhp19_sample.py \
  --event /mnt/d/DHP19/DVS_movies/S1/session1/mov1.aedat \
  --label /mnt/d/DHP19/Vicon_data/S1_1_1.mat \
  --projection-dir /mnt/d/DHP19/P_matrices \
  --output-dir /mnt/d/DHP19_preprocessed/verification/S1_session1_mov1_20frames \
  --frames 20
```

不要直接用旧的 `scripts/data/dhp19_dataset.py` 代替这个命令。旧文件仍是尺寸和标签均未校准的历史原型。

## 4. 输出文件说明

默认输出目录中应有 9 个文件：

| 文件 | 内容 |
|---|---|
| `S1_session1_mov1_7500events_first20.h5` | 事件帧，数据集键为 `/DVS` |
| `S1_session1_mov1_7500events_first20_label.h5` | 对齐后的 3D 姿态，数据集键为 `/XYZ` |
| `overlay_frame_0000/0009/0019.png` | 官方完整事件帧和区间平均姿态，主要用于复现官方标签逻辑 |
| `alignment_peak_100ms_frame_0000/0009/0019.png` | 帧内事件最密集的 100 ms 和同一时刻姿态，用于检查时间与投影对齐 |
| `summary.json` | 输入指纹、环境版本、过滤统计、时间范围、投影和短窗诊断信息 |

HDF5 的 Python 轴顺序为：

```text
/DVS  shape=(20, 260, 346, 4)  dtype=uint8
      轴顺序=(帧, 高, 宽, 相机通道)

/XYZ  shape=(20, 3, 13)        dtype=float32
      轴顺序=(帧, XYZ坐标, 关节)
```

13 个关节的顺序是：

```text
head, shoulderR, shoulderL, elbowR, elbowL,
hipR, hipL, handR, handL, kneeR, kneeL, footR, footL
```

每个完整事件帧由四个相机通道合计 30,000 个保留事件构成，即每个通道 7,500 个事件。Vicon 姿态标签按对应事件帧的时间区间求均值。

## 5. 相机通道与投影矩阵

DHP19 文件内部的相机通道顺序和投影矩阵文件名不是简单的 `0 -> P1` 顺序。本项目按官方数据代码使用：

| 事件通道 | 投影矩阵 |
|---:|---|
| 0 | `P4.npy` |
| 1 | `P1.npy` |
| 2 | `P3.npy` |
| 3 | `P2.npy` |

不要自行改成顺序映射，否则骨架会投到错误的相机画面。

## 6. 如何判断结果是否合理

先在 Windows 中打开三张 `alignment_peak_100ms_frame_*.png`。每张图包含四个相机视角，活动肢体的红色关节点和绿色骨架应沿着白色事件轨迹分布。

事件相机只记录亮度变化，不会像普通相机一样持续显示完整人体。不动的躯干或四肢可能是黑色区域，因此不能要求整副骨架的每条线都压在白色像素上。

`overlay_frame_*.png` 使用官方的 30,000 事件完整帧和整个时间区间的平均姿态。本样本中单帧实际覆盖约 `192-1613 ms`，移动的手部在一帧内最多可跨越约 `14-38 px`。完整帧会形成运动轨迹，而一副平均骨架只代表这段轨迹的中心，二者不可能逐像素重合。

本机首次验证结果如下：

```text
20 个事件帧均非空
每帧非零像素数范围：5085 至 7963
三个检查帧的四个视角均有 13 个关节落在画面内
三个峰值 100 ms 窗口分别包含：13162、12126、9802 个事件
事件数据：shape=(20, 260, 346, 4)，uint8
姿态标签：shape=(20, 3, 13)，float32，全部为有限值
```

峰值 100 ms 图中的活动手臂与事件轨迹吻合，没有发现固定的上下翻转、相机通道错配或整体时间偏移。黑色区域中的静止骨架不能据此判定为错位。

`summary.json` 还记录了：

- 原始输入文件大小和 SHA-256；
- 同步开始和结束时间；
- 热像素、背景噪声和红外区域过滤数量；
- 每帧事件时间范围；
- 每帧使用的 Vicon 样本范围；
- Python 包版本和通道投影映射。
- 峰值 100 ms 的起止时间、事件数量和对应 Vicon 样本编号。

这些信息用于后续批量处理时追溯结果，不应手工修改。

## 7. 运行测试

修改数据处理代码后，先运行：

```bash
cd /mnt/d/EventPoseFinal
/home/mestia/miniconda3/bin/conda run -n eventpose-dhp19 \
  python -m pytest tests/data -q
```

当前 28 项测试覆盖 AEDAT2 解码、同步规则、官方过滤、固定事件数量成帧、峰值时间窗、Vicon 加载、姿态均值、同时刻姿态、投影关系、HDF5 原子写入和叠加图生成。

## 8. 常见问题

### 提示找不到 Conda

确认 WSL 中存在：

```text
/home/mestia/miniconda3/bin/conda
```

如果 Miniconda 安装到了其他位置，需要同时修改环境安装脚本和上面的运行命令。

### 提示输入文件不存在

先在 Windows 检查 `D:\DHP19` 下的事件、Vicon 和投影矩阵路径是否完整。WSL 中对应路径以 `/mnt/d/` 开头。

### 生成的图中骨架明显偏离人体

先确认查看的是 `alignment_peak_100ms_frame_*.png`，并只比较产生事件的活动肢体。若活动肢体仍出现同方向、跨多个视角的明显偏移，不要直接开始训练；依次检查事件文件和 MAT 文件是否属于同一个 `S/Session/Move`，确认通道映射仍为 `P4/P1/P3/P2`，再检查同步事件和 Vicon 时间范围。

### 是否已经可以训练

还不可以直接进入正式训练。目前只证明第一组数据的读取、过滤、成帧、姿态对齐和投影链路可用。下一步应把同样的验证扩展到不同受试者、动作和会话，再实现可恢复的批量预处理、训练/验证划分和训练环境。
