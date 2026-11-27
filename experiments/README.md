# 实验记录

当前 `registry.csv` 分别记录助手的 [64 帧四视角 CPU 演示](../results/example/record.md) 和用户的 [30 帧双视角 Colab 演示](../results/user_colab/20261127T044151Z/record.md)。用户第一次运行的四个原始文件已核查；第二次 [局部 +x 5 cm 对照](../results/user_colab/20261127T054546Z_shift_x5cm/record.md) 的五个原始文件也已核查并登记。两次用户运行均已完成，本阶段已收尾。`runs/` 用于保存后续实验的配置、计划和证据索引。

## 建立计划记录

在仓库根目录运行：

```bash
python3 scripts/new_experiment.py --id EXP-001 --title "双相机采集流程验证"
```

该命令会复制配置草案，生成 `experiments/runs/EXP-001/` 下的 `config.json`、`metadata.json`、`record.md`，并在登记表追加 `planned` 行。它**不会**运行仿真、调用模型或计算评分。实验 ID 已存在时拒绝覆盖；可用 `--config` 指定其他 JSON 配置。

执行前补全配置，并记录实际代码版本、运行环境、种子、初始状态、成功判定和资源预算。执行后手动同步 `metadata.json`、`record.md`、`registry.csv` 的状态，例如 `running`、`completed`、`failed`、`blocked`；失败记录也保留。这个初始化工具不会代替结果审核。

## 检查当前机器的软件信息

```bash
python3 scripts/check_environment.py
```

需要保存为新文件时：

```bash
python3 scripts/check_environment.py --output experiments/runs/EXP-001/environment.json
```

检查结果只代表执行命令的那台机器。工具查询已安装包的元数据，不导入模拟器，不启动渲染，也不验证 GPU 或环境能否运行；没有安装任何软件。指定输出文件已存在时拒绝覆盖。

## 结果边界

截图和双相机数据采集可证明采集流程的部分功能；它们不能单独证明 VLA 鲁棒性。策略评测须有真实执行、对照条件和可核对的 episode 结果。原始大文件保留在数据/产物目录，在记录中引用，不把下载资源或密钥放进提交。

记录工具用于单人串行建档，请不要同时运行多个建档命令。多人并行时先为实验分配不重复 ID，并通过正常 Git 合并审阅登记表。
