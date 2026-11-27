#!/usr/bin/env python3
"""Build the self-contained Colab notebook from the actual demo source.

Regenerate after changing scripts/run_demo.py. This command does not run the
simulation, install packages, access an account, or upload any file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parents[1]


def cell(kind: str, identifier: str, source: str, *, hidden: bool = False) -> dict:
    item = {
        "cell_type": kind,
        "id": identifier,
        "metadata": {"jupyter": {"source_hidden": True}} if hidden else {},
        "source": textwrap.dedent(source).strip() + "\n",
    }
    if kind == "code":
        item.update(execution_count=None, outputs=[])
    return item


def main() -> None:
    source_path = ROOT / "scripts" / "run_demo.py"
    source = source_path.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    cells = [
        cell("markdown", "start-here", """
            # 机械臂仿真：运行一次，看看相机画面

            在 Google Colab 中上传这个 `.ipynb` 文件，使用普通 **CPU** 运行时，
            按顺序运行下面的代码单元。无需在自己的 Mac 上安装机械臂软件。

            本文件已包含本次演示脚本，无需连接 GitHub 或 Google Drive。
            第一次运行会下载 Python 和依赖；仿真在当前云端机器运行。
            完成后，下方会直接显示四格动图和截图。

            **这次做什么：** 用 PyBullet 自带的 Franka Panda 模型执行预先设置的关节运动，
            对比固定相机、原始手腕相机、手腕相机局部 x 方向 +5 cm、局部 y 方向 +15°。
            四幅画面来自同一时刻的场景状态。

            **如何解释：** 这用于观察相机视角、目标可见性和遮挡；
            没有训练 VLA，也没有把机械臂运动当成抓取成功。
            师兄提供的 RP 仅是外部参考，本笔记本不包含其原文。

            本笔记本保存时未执行，实际是否成功以你的运行输出为准。
        """),
        cell("markdown", "install-heading", """
            ## 1. 准备运行环境

            这里使用 Python 3.11 的独立环境，避免 Colab 自身 Python 版本改变后，
            PyBullet 需要从源码编译。安装只作用于本次云端运行时。
        """),
        cell("code", "install-environment", """
            import importlib.util
            from pathlib import Path
            import platform
            import subprocess
            import sys

            if platform.system() != "Linux":
                raise RuntimeError("请把这个文件上传到 Google Colab 的 Linux CPU 运行时，再运行本单元。")

            WORK = Path.cwd() / "robot_arm_demo"
            WORK.mkdir(exist_ok=True)
            if importlib.util.find_spec("uv") is None:
                subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "uv"], check=True)

            UV = [sys.executable, "-m", "uv"]
            subprocess.run(UV + ["python", "install", "3.11"], check=True)
            VENV = WORK / ".venv-py311"
            PYTHON = VENV / "bin" / "python"
            if not PYTHON.exists():
                subprocess.run(UV + ["venv", "--python", "3.11", str(VENV)], check=True)
            subprocess.run(UV + [
                "pip", "install", "--python", str(PYTHON), "--only-binary", ":all:",
                "pybullet==3.2.7", "numpy==2.4.6", "Pillow==13.0.0",
            ], check=True)
            subprocess.run([str(PYTHON), "--version"], check=True)
            print("环境已准备。下面将写入演示脚本。")
        """),
        cell("markdown", "source-heading", """
            ## 2. 写入演示脚本

            运行下面这一格即可。它包含仓库 `scripts/run_demo.py` 的完整副本，
            并检查内容哈希。重复运行会更新这份脚本；后续每次仿真会创建新的结果文件夹。
        """),
        cell("code", "write-demo-source", (
            "import hashlib\n"
            f"DEMO_SOURCE = {source!r}\n"
            f"EXPECTED_SHA256 = {source_hash!r}\n"
            "assert hashlib.sha256(DEMO_SOURCE.encode('utf-8')).hexdigest() == EXPECTED_SHA256\n"
            "SCRIPT = WORK / 'scripts' / 'run_demo.py'\n"
            "SCRIPT.parent.mkdir(exist_ok=True)\n"
            "SCRIPT.write_text(DEMO_SOURCE, encoding='utf-8')\n"
            "print('脚本已写入：', SCRIPT)\n"
            "print('SHA-256：', EXPECTED_SHA256)\n"
        ), hidden=True),
        cell("markdown", "run-heading", """
            ## 3. 跑一次仿真

            首次直接使用默认设置。`FRAMES` 决定采集帧数，`FPS` 决定动图播放速度。
            保留小分辨率即可；这次不需要 GPU。

            等单元完成后，会显示本次结果的文件夹。若出现错误，保留完整错误文字，
            不要把安装完成或出现部分文件当成仿真成功。
        """),
        cell("code", "run-simulation", """
            FRAMES = 64
            FPS = 12
            WIDTH, HEIGHT = 360, 280
            SEED = 7  # 本演示不随机采样；这个数字作为记录标识。

            RESULTS = WORK / "results" / "demo"
            RESULTS.mkdir(parents=True, exist_ok=True)
            before = set(RESULTS.glob("*/metadata.json"))
            command = [
                str(PYTHON), str(SCRIPT), "--output", str(RESULTS),
                "--frames", str(FRAMES), "--fps", str(FPS),
                "--width", str(WIDTH), "--height", str(HEIGHT), "--seed", str(SEED),
            ]
            print("正在运行：", " ".join(command), flush=True)
            subprocess.run(command, cwd=WORK, check=True)
            created = set(RESULTS.glob("*/metadata.json")) - before
            if len(created) != 1:
                raise RuntimeError("没有找到唯一的新运行记录，请查看上方输出及结果目录。")
            RUN_DIR = created.pop().parent
            print("本次结果：", RUN_DIR)
        """),
        cell("markdown", "view-heading", """
            ## 4. 看效果

            - **左上：** 固定外部相机，可以看到整个机械臂运动。
            - **右上：** 原始手腕相机，随末端一起移动。
            - **左下：** 在原始安装上，沿相机局部 x 轴平移 +5 cm。
            - **右下：** 在原始安装上，绕相机局部 y 轴旋转 +15°。

            先看方块是否仍在画面里、位置怎样改变，以及手臂有没有挡住相机。
            这些是图像观察，不是模型性能分数。
        """),
        cell("code", "show-results", """
            import json
            from IPython.display import Image, display

            display(Image(filename=str(RUN_DIR / "comparison.gif")))
            display(Image(filename=str(RUN_DIR / "comparison.png")))
            record = json.loads((RUN_DIR / "metadata.json").read_text(encoding="utf-8"))
            print("结果文件：")
            for path in sorted(RUN_DIR.iterdir()):
                print(" -", path.name)
            print("metadata.json 保存软件版本、运行信息和逐帧几何记录。")
        """),
        cell("markdown", "download-heading", """
            ## 5. 可选：保存这次结果

            云端运行时可能被回收。想把结果留在自己电脑上时，将下方
            `DOWNLOAD_RESULTS` 改成 `True`，再运行这一格。
            它只打包本次结果，不包含 Python 环境或第三方模型文件。
        """),
        cell("code", "download-results", """
            DOWNLOAD_RESULTS = False

            if DOWNLOAD_RESULTS:
                import shutil
                archive = shutil.make_archive(str(WORK / RUN_DIR.name), "zip", root_dir=RUN_DIR)
                try:
                    from google.colab import files
                except ImportError:
                    print("结果压缩包：", archive)
                else:
                    files.download(archive)
            else:
                print("本次没有触发下载；上方动图和截图仍可查看。")
        """),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "colab": {"name": "robot_arm_demo.ipynb", "provenance": []},
            "demo_source": {"path": "scripts/run_demo.py", "sha256": source_hash},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    destination = ROOT / "notebooks" / "robot_arm_demo.ipynb"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"notebook": str(destination), "script_sha256": source_hash, "executed": False}))


if __name__ == "__main__":
    main()
