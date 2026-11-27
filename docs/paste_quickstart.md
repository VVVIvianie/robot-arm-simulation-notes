# 上传不了 Notebook 时：复制一格代码运行

如果 `.ipynb` 无法上传，可以新建一个空白 Colab 笔记本，把 [colab_paste_cell.py](../scripts/colab_paste_cell.py) 的全部文本复制进一个代码格，点击左侧 ▶ 运行。

代码会在当前 Linux 云端环境里安装独立 Python 3.11 及仿真依赖，再运行 30 帧双视角演示并在代码格下方显示动图（左侧固定相机，右侧手腕相机）。请保留默认 CPU 运行时。

这是帮助开始运行的简化入口。完整四路相机对照仍在 [原 Notebook](../notebooks/robot_arm_demo.ipynb) 和 [run_demo.py](../scripts/run_demo.py)。不需要通过更改仓库可见性、GitHub 授权或上传文件来执行这个粘贴入口。

目前无法仅凭“上传不了”判断原失败发生在文件下载、文件选择还是 Colab 接收阶段。这个入口跳过文件上传步骤；不会修复 Google 账号登录或运行时连接问题。若代码格也无法运行，请保留具体错误文字或截图。

用户自己在 Colab 的运行状态，以其页面的实际输出为准。

本入口已在助手 Linux 环境实际运行，验证摘要见 [paste_entry_check.json](../results/paste_entry_check.json)。用户也已在 Colab 完成 30 帧双视角运行，并上传 GIF、PNG、demo.py 和 metadata.json；四个原始文件的一致性已核对，上传源码与本入口内嵌的演示源码相同。见 [用户实际记录](../results/user_colab/20261127T044151Z/record.md) 与 [过程日志](../logs/2026-11-27-user-colab.md)。这次运行不包含四路版本中的相机安装变化对照。

## 画面显示不全，或需要保存结果

在同一笔记本下面新增一个代码格，粘贴 [colab_view_save.py](../scripts/colab_view_save.py) 的全部内容运行。它将当前 GIF 适配页面宽度，并把 `run` 指向的这一次结果打包为 ZIP 触发浏览器下载。不会把 Python 虚拟环境打包进去，也不会重新运行仿真。

结果包应包含 `comparison.gif`、`comparison.png`、`demo.py` 与 `metadata.json`。请以实际下载到电脑的文件为准；尚未下载成功时，不把云端文件当作已经完成本地保存。
