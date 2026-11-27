# 第一次运行：在哪里跑，怎么看

GitHub 保存代码和记录。实际执行需要 Python 环境；运行结束后查看生成的 GIF、PNG 和 JSON。

## 先看已有演示

仓库的 `results/example/` 保存助手首次完成的 64 帧四视角演示。用户在 Colab 完成的 30 帧双视角快速演示单独保存在 [用户实际记录](../results/user_colab/20261127T044151Z/record.md)，原始 GIF、PNG、源码和元数据已核对。打开对应目录的 `comparison.gif` 看运动、`comparison.png` 看同一时刻的视角。这些均为预编程关节运动和相机观察，尚未进行抓取任务或 VLA 模型评测；用户也已完成 [局部 +x 5 cm 对照](../results/user_colab/20261127T054546Z_shift_x5cm/record.md)。本阶段两次运行已收尾，以下说明供复现时参考。

## 上传不了文件时

使用 [复制一格代码运行](paste_quickstart.md) 的入口，新建空白 Colab 笔记本即可开始。

## 推荐入口：用浏览器运行 Notebook

1. 下载本仓库的 [robot_arm_demo.ipynb](../notebooks/robot_arm_demo.ipynb)。
2. 打开 [Google Colab](https://colab.research.google.com/)，选择 **File → Upload notebook**，上传下载的文件。
3. 使用默认 CPU 运行时，按顺序运行所有代码单元。
4. 安装单元会在云端准备独立 Python 3.11 环境，后续单元执行仿真并直接显示动图和截图。
5. 需要保存本次结果时，再运行最后的下载单元。

Notebook 自带此版本的演示代码，不需要克隆私有仓库、输入 GitHub 验证码或挂载网盘。它与 `scripts/run_demo.py` 使用同一份源码，由 `scripts/build_notebook.py` 生成。完整 Notebook 在助手的 Linux Python 3.11 环境完成运行验证；用户的 30 帧双视角复制粘贴入口已经运行，原始产物也已核对，完整四视角 Notebook 未作为用户本阶段实验执行。

如果使用 Mac，这条路径会把计算放在云端，不要求先在 Mac 编译 PyBullet。

## 已有 Linux / NCC Python 环境时

在终端进入仓库根目录。已有 Python 3.11 时：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.txt
python scripts/run_demo.py
```

若安装了 uv，也可以：

```bash
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python --only-binary=:all: -r requirements.txt
.venv/bin/python scripts/run_demo.py
```

这组安装命令在 Linux x86_64 验证。官方 PyBullet 3.2.7 为该平台的 Python 3.11 提供 wheel；Python 3.12 或 Mac 上可能需要源码构建，因此不把同一组命令当作已经验证的 Mac 安装方法。首次安装报错时保留错误原文。

每次运行会新建：

```text
results/demo/run_日期时间/
```

| 文件 | 用途 |
| --- | --- |
| `comparison.gif` | 机械臂运动和四路画面的动态对比 |
| `comparison.png` | 同一时刻的四格截图 |
| `external.png` | 外部固定相机 |
| `wrist_baseline.png` | 随末端运动的原始手腕相机 |
| `wrist_tx_plus_5cm.png` | 安装位置在原相机局部 x 方向移动 5 cm |
| `wrist_ry_plus_15deg.png` | 安装方向绕原相机局部 y 轴旋转 15° |
| `metadata.json` | 运行环境、源码指纹、关节状态、逐帧相机位置与可见像素 |

四路图像来自相同仿真状态，拍摄间不推进物理时间。手腕相机只在初始化时确定安装关系，之后随机械臂运动；它不会每帧自动重新瞄准目标。

## 在带桌面的电脑上看 3D 窗口

在 PyBullet 安装成功且桌面可用的机器上：

```bash
python scripts/run_demo.py --gui --keep-open
```

运行结束后会保存图片，并保留 3D 窗口直到关闭。这里验证了无窗口渲染；尚未在你的 Mac 或 NCC 桌面上验证 GUI。

## 第一遍看这四件事

- 机械臂是否实际移动。
- 固定相机和手腕相机的图像为何不同。
- 平移或旋转相机后，方块在画面中的位置如何变化。
- 有没有方块接近边缘、出画或被遮挡。

记录“观察到什么”，并保留对应输出。仅凭这次演示不能得到抓取成功率或 VLA 性能结论。

## 官方参考

- [PyBullet Quickstart Guide](https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstart_guide/PyBulletQuickstartGuide.md.html)：DIRECT、GUI 与 TinyRenderer。
- [PyBullet 3.2.7 发布文件](https://pypi.org/project/pybullet/3.2.7/)：Python 与平台 wheel。
- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html)：上传已有 Notebook。
- [uv Python 安装文档](https://docs.astral.sh/uv/guides/install-python/)：独立 Python 版本安装。
