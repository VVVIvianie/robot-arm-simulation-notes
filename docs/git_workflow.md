# 记录自己的模拟实验

当前仓库：[robot-arm-simulation-notes](https://github.com/VVVIvianie/robot-arm-simulation-notes)。

公开版从审查后的当前文件快照建立独立历史。早期私有仓库作为备份保留，旧 checkout 继续指向私有备份；公开版使用新 checkout。不要把旧分支或旧提交合并进公开版，以免重新引入外部 RP。

本阶段两次仿真已经结束；以下命令供后续用户明确要求继续修改时参考。

每次做完一小步，保存实际修改的代码、使用的配置和观察记录，再提交。引用别人的方案或代码时保留来源说明；师兄发来的 RP 不作为自己的作品上传。

```bash
git status --short
git diff
git add <本次要提交的文件>
git diff --cached
git commit -m "描述本次真实完成的工作"
git push
```

可以用 `scripts/new_experiment.py` 建立计划记录，实际运行后再补齐结果、报错和下一步。不要把仅建档的条目改称实验完成。
