# EventPoseFinal

事件相机人体姿态估计研究项目。这个目录是整理后的统一入口，负责保存项目代码、配置、说明文档和诊断脚本；大型数据集、OpenEB SDK、第三方仓库和 Python 环境仍保留在 D 盘原位置。

本文重点说明 `environment`、`scripts` 和 `tests/fixtures` 中的**项目自写辅助文件**如何使用，以及它们和 OpenEB 官方工具的区别。

## 1. 推荐的第一次运行顺序

### 第一步：检查 Windows OpenEB

在 PowerShell 中运行：

```powershell
& D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1
```

预期输出包括：

```text
OpenEB version: 5.2.0
HAL plugin: found
EVT2 round-trip: 10 events
Python Stream import: OK (3.11.6)
Camera: not connected (expected until hardware is available)
```

这一步使用 OpenEB 官方的 EVT2 编码器、解码器和文件信息工具生成一个临时的 10 事件文件，然后自动删除临时文件。它验证的是 SDK 本身，不需要相机。

### 第二步：检查 WSL 环境

在 WSL Ubuntu 中运行：

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
```

当前已知状态：

- Python `3.14.6`；
- NumPy `2.4.4`；
- PyTorch `2.11.0+cu128`；
- CUDA 可用；
- `cv2`、`mmengine`、`mmpose` 尚未安装。

该脚本只读取状态，不安装软件，也不会修改 Conda 环境。

### 第三步：再运行项目原型

先确认输入文件存在、输出位置正确，并阅读下方每个脚本的限制。原型脚本不建议直接用于大规模数据处理。

## 2. `environment/windows` 文件详解

### 2.1 `Set-OpenEBEnvironment.ps1`

路径：`environment/windows/Set-OpenEBEnvironment.ps1`

作用：为**当前 PowerShell 进程**临时配置 OpenEB 所需路径，包括：

- OpenEB Release 可执行文件；
- OpenEB 动态库；
- Python 扩展模块；
- `MV_HAL_PLUGIN_PATH`；
- `HDF5_PLUGIN_PATH`；
- OpenEB 使用的 vcpkg DLL 目录。

它不会永久修改 Windows 系统环境变量，也不会重新编译 OpenEB。

通常不需要单独运行。其他 Windows 脚本会自动加载它。如果需要在当前窗口手动准备环境，可以运行：

```powershell
. D:\EventPoseFinal\environment\windows\Set-OpenEBEnvironment.ps1
```

注意开头的点号和空格：这是把脚本加载到当前 PowerShell，而不是开启一个无关的子进程。

### 2.2 `Open-EventPoseShell.ps1`

路径：`environment/windows/Open-EventPoseShell.ps1`

作用：加载 OpenEB 环境后，打开一个新的 PowerShell 窗口，并把工作目录切换到 `D:\EventPoseFinal`。

运行：

```powershell
& D:\EventPoseFinal\environment\windows\Open-EventPoseShell.ps1
```

适合需要连续运行多个 Windows OpenEB 命令的情况。它只影响新打开的窗口，关闭窗口后环境变量不会永久保存。

如果 Windows 执行策略阻止脚本，可以在 PowerShell 中使用一次性绕过方式：

```powershell
powershell.exe -ExecutionPolicy Bypass -File D:\EventPoseFinal\environment\windows\Open-EventPoseShell.ps1
```

### 2.3 `Test-OpenEB.ps1`

路径：`environment/windows/Test-OpenEB.ps1`

作用：这是项目自己的 OpenEB 健康检查包装器，内部调用的是 OpenEB 官方工具。它会检查：

1. OpenEB 版本是否为 `5.2.0`；
2. Prophesee HAL 插件是否存在；
3. 官方 EVT2 编码器能否生成 RAW；
4. 官方 EVT2 解码器能否还原 10 个事件；
5. 官方文件信息工具能否读取 RAW；
6. `metavision_sdk_stream` Python 模块能否导入；
7. HAL 是否发现相机。

无相机时出现 `Camera: not connected` 是正常结果，不代表 SDK 失败。连接真实相机后重新运行即可检查设备枚举。

## 3. `environment/wsl` 文件详解

### `check_environment.sh`

路径：`environment/wsl/check_environment.sh`

作用：只读检查 WSL 是否能访问共享项目和数据，并报告核心/可选 Python 包。

默认使用：

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
```

也可以显式指定 Python：

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh \
  /home/mestia/miniconda3/bin/python
```

输出含义：

```text
path=ok ...                  路径存在
path=missing ...             路径不存在
package=ok numpy ...         核心包可导入
package=missing torch ...    核心包不可导入，脚本返回非零状态
optional=ok mmpose ...       可选训练包可导入
optional=missing mmpose      可选训练包尚未安装
cuda_available=True          PyTorch 能看到 CUDA
```

它不会安装 `mmpose`、`mmengine` 或 `opencv`。这些包应在确定 Python、CUDA 和 MMPose 版本组合后，再创建独立的训练环境。

## 4. `scripts/data` 文件详解

### 4.1 `dhp19_dataset.py`

路径：`scripts/data/dhp19_dataset.py`

作用：读取旧式 `.aedat` 文件，并尝试转换为 PyTorch 体素网格，同时包装成 `Dataset`。

代码中的关键假设：

- 相机尺寸默认为宽 `240`、高 `180`；
- 事件地址和时间戳按当前函数中的 32 位数据布局解析；
- 体素默认分为 `5` 个时间 bin；
- 极性被映射到 `-1/+1`；
- 数据集标签目前是 `13 x 3` 的全零占位值。

因此它当前只能作为**解析和体素转换原型**，不能作为正式 DHP19 姿态数据集。特别是：

- 全零标签不是真实人体关节标注；
- 文件格式、位移规则和数据尺寸需要用实际 DHP19 文件核对；
- `__main__` 中的路径是 WSL 示例路径；
- 运行前应确认目录里确实有 `.aedat` 文件。

查看语法而不执行数据读取：

```powershell
& D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe -m py_compile `
  D:\EventPoseFinal\scripts\data\dhp19_dataset.py
```

### 4.2 `event_to_voxel.py`

路径：`scripts/data/event_to_voxel.py`

作用：把结构化事件数组转换成 `(num_bins, height, width)` 的 NumPy 体素网格。

直接运行：

```powershell
& D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe `
  D:\EventPoseFinal\scripts\data\event_to_voxel.py
```

它会在内存中随机生成 50,000 个事件，输出体素形状和非零点数量。这是功能演示，不是 DHP19 实际数据处理，也不会读取数据集。

### 4.3 `view_npy.py`

路径：`scripts/data/view_npy.py`

作用：读取一个 NPY 体素文件，并把每个通道保存成 PNG 预览图。

当前脚本内置了示例路径：

```text
/mnt/d/DHP19_preprocessed/S1/session1/mov1/frame_00001.npy
```

在 WSL 中运行：

```bash
python /mnt/d/EventPoseFinal/scripts/data/view_npy.py
```

输出会写到输入文件旁边的 `viewed` 子目录。运行前请确认该 NPY 文件实际存在；如果要查看其他样本，需要先修改脚本里的 `npy_path`。

注意：这个脚本会在数据集目录中创建输出目录，因此不要在原始数据上批量运行。正式使用前应把输入和输出改成命令行参数，并把图片写入项目外的实验输出目录。

## 5. `scripts/diagnostics` 文件详解

### 5.1 `test_camera.py`

路径：`scripts/diagnostics/test_camera.py`

作用：通过 `metavision_sdk_stream.Camera.from_first_available()` 尝试打开第一台可用相机。

运行前先打开已经加载 OpenEB 环境的 PowerShell：

```powershell
& D:\EventPoseFinal\environment\windows\Open-EventPoseShell.ps1
& D:\EventPoseFinal\scripts\diagnostics\test_camera.py
```

第二条命令实际上需要 Python 解释器，推荐明确写出：

```powershell
& D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe `
  D:\EventPoseFinal\scripts\diagnostics\test_camera.py
```

没有相机时会捕获异常并提示检查设备连接。当前没有相机，所以不要把“没有设备”当作代码失败。

连接相机后，这个脚本只证明设备流可以开始读取，不会完成录制、保存、滤波或姿态估计。

### 5.2 `generate_invalid_raw.py`

路径：`scripts/diagnostics/generate_invalid_raw.py`

这是从旧文件 `generate_raw.py` 改名后的**风险标记副本**。它生成一个带文本头和 NumPy 结构体数据的自定义文件，文件名虽然包含 `raw`，但不是 OpenEB 官方 RAW 格式。

不要用它测试 OpenEB，也不要把输出上传为真实传感器 RAW。需要有效测试 RAW 时，应运行：

```powershell
& D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1
```

该诊断脚本使用 OpenEB 自带的 EVT2 encoder 生成官方工具可以读取的 RAW。

### 5.3 `filter_benchmark_demo.py`

路径：`scripts/diagnostics/filter_benchmark_demo.py`

这个文件只打印预设的事件数量、吞吐量、噪声滤除率、SNR 和 GPU 负载等数字，并没有读取事件、调用滤波器或进行真实测量。

因此：

- 不要把输出写进实验结果；
- 不要把它作为滤波算法已经完成的证据；
- 不要据此比较不同算法性能。

它只适合帮助回忆以前的实验设想。正式 benchmark 必须重新读取真实输入，记录实际运行时间，并保存原始数据、参数和版本信息。

## 6. `tests/fixtures` 文件详解

### `test_dummy.invalid.raw`

路径：`tests/fixtures/test_dummy.invalid.raw`

这是旧项目留下的自定义字节流，已经特意改名为 `.invalid.raw` 来提醒使用者：它不是 OpenEB 有效 RAW fixture。

它的用途仅限于：

- 保留历史文件，方便追溯；
- 测试某些“文件存在/文件复制/哈希校验”逻辑。

它不能用于：

- 测试 OpenEB RAW 解码；
- 验证相机数据格式；
- 计算事件数量、吞吐量或噪声比例。

## 7. 一套安全的实际操作流程

### A. 只检查环境

```powershell
& D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1
```

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
```

### B. 只运行内存演示

```powershell
& D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe `
  D:\EventPoseFinal\scripts\data\event_to_voxel.py
```

该步骤不碰 DHP19 数据，风险最低。

### C. 查看一个 NPY 样本

1. 在 WSL 中确认 `/mnt/d/DHP19_preprocessed/.../frame_00001.npy` 存在；
2. 检查 `view_npy.py` 中的 `npy_path`；
3. 运行脚本；
4. 到输入文件旁的 `viewed` 目录查看 PNG；
5. 查看完成后可删除 `viewed` 输出，避免污染数据集目录。

### D. 处理真实事件文件

在运行 `dhp19_dataset.py` 前，必须先确认：

- 实际文件扩展名和格式确实是 `.aedat`；
- 文件地址布局与脚本假设一致；
- 相机分辨率不是其他尺寸；
- 时间戳单位和排序方式正确；
- 标签来源已经找到并能和事件样本对齐。

否则只能把结果当作调试输出，不能进入训练。

### E. 连接真实相机后

1. 运行 `Test-OpenEB.ps1` 确认 SDK 仍正常；
2. 运行 `test_camera.py` 检查相机枚举；
3. 再使用 OpenEB 官方录制/转换工具保存数据；
4. 不要先运行旧的 `generate_invalid_raw.py` 代替真实数据。

## 8. 常见问题

### PowerShell 提示脚本不能运行

使用一次性执行策略：

```powershell
powershell.exe -ExecutionPolicy Bypass -File D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1
```

### OpenEB 报 DLL 或插件找不到

确认使用的是项目脚本，而不是直接双击某个 `.exe`：

```powershell
& D:\EventPoseFinal\environment\windows\Test-OpenEB.ps1
```

如果仍失败，检查以下路径是否存在：

```text
D:\OpenEB_Dev\openeb\build\lib\metavision\hal\plugins
D:\OpenEB_Dev\openeb\build\lib\hdf5\plugin
D:\OpenEB_Dev\openeb\py3venv\Scripts\python.exe
```

### `Camera: not connected`

当前没有物理相机，这是预期状态。它只表示没有可枚举设备，不表示 OpenEB 安装失败。官方 EVT2 文件测试仍然可以在无相机时运行。

### WSL 显示 `optional=missing mmpose`

这是当前已知状态。不要直接把任意版本的 MMPose 安装到现有 base 环境。后续应先确定 Python、PyTorch、CUDA、MMEngine 和 MMPose 的兼容矩阵，再创建独立环境。

### `view_npy.py` 找不到文件

脚本中的 NPY 路径只是示例。请先查找真实文件：

```bash
find /mnt/d/DHP19_preprocessed -name 'frame_00001.npy' | head
```

然后修改脚本里的 `npy_path`，或后续将脚本改造成接收命令行参数。

### `dhp19_dataset.py` 能运行但标签全是零

这是当前代码明确存在的占位行为，不是模型预测结果。真实训练前必须补充 DHP19 姿态标签读取、坐标系转换、样本对齐和训练/验证划分。

## 9. 官方工具和自写文件的区别

| 内容 | 官方/自写 | 用途 | 当前可信度 |
|---|---|---|---|
| `metavision_evt2_raw_file_encoder.exe` | OpenEB 官方 | 生成有效 EVT2 RAW | 可用于 SDK 检查 |
| `metavision_evt2_raw_file_decoder.exe` | OpenEB 官方 | 解码 EVT2 RAW | 可用于 SDK 检查 |
| `metavision_file_info.exe` | OpenEB 官方 | 查看事件文件信息 | 可用于 SDK 检查 |
| `Test-OpenEB.ps1` | 项目自写包装器 | 串联官方工具做健康检查 | 已在本机验证 |
| `check_environment.sh` | 项目自写 | 报告 WSL 环境状态 | 只读检查 |
| `dhp19_dataset.py` | 项目原型 | AEDAT 解析和体素转换 | 标签仍是占位 |
| `event_to_voxel.py` | 项目演示 | 随机数据体素转换 | 不是实际数据 benchmark |
| `view_npy.py` | 项目原型 | 查看 NPY 通道 | 路径硬编码 |
| `test_camera.py` | 项目原型 | 尝试打开相机 | 无相机时正常退出 |
| `generate_invalid_raw.py` | 历史演示 | 生成自定义伪 RAW | 不是 OpenEB RAW |
| `filter_benchmark_demo.py` | 历史演示 | 打印预设数字 | 不是实际 benchmark |
| `test_dummy.invalid.raw` | 历史 fixture | 保留和追溯 | 明确无效 |


## 10. 文件来源和保存策略

- 原始来源和目标路径记录在 `docs/inventory/assets.tsv`；
- 历史 DOCX 只作为参考，已验证的说明放在 `docs/setup`；
- 数据集、第三方仓库、环境、模型和实验输出不进入 Git；
- 本次整理不删除旧项目、不移动数据、不重建 OpenEB、不推送 GitHub。
