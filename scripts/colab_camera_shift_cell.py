# 在刚才跑通双视角仿真的同一个 Colab 笔记本中，新增代码格并粘贴全部内容。
# 本次只比较：原始手腕相机 vs 沿其光学局部 +x 平移 5 cm；方向保持相同。
from pathlib import Path
from datetime import datetime, timezone
from IPython.display import HTML, display
from google.colab import files
import base64, hashlib, json, shutil, subprocess

base_sha = "03d2abfb35bd68be8b43d6c80a8730f337c9cf7ba1b93f5110df5accd844f055"
shift_work = Path.cwd() / "robot_arm_no_upload"
base_script = next((p for p in sorted(shift_work.glob("run_*/demo.py"), reverse=True)
                    if hashlib.sha256(p.read_bytes()).hexdigest() == base_sha), None)
shift_python = shift_work / ".venv" / "bin" / "python"
if base_script is None or not shift_python.exists():
    raise RuntimeError("请先运行之前生成双视角动图的第一格代码，再运行这一格。")
shift_source = base_script.read_text(encoding="utf-8")

shift_changes = [
    ('labels = ["Fixed camera", "Wrist camera"]',
     'shift = np.eye(4)\nshift[0, 3] = 0.05\n'
     'labels = ["Wrist baseline", "Wrist +5cm local x"]'),
    ('cameras = [external, wrist]', 'cameras = [wrist, wrist @ shift]'),
    ('30-frame two-view quick demo; prescribed motion; no learned policy or grasp evaluation',
     '30-frame wrist mounting comparison; local optical x +0.05 m; same orientation; '
     'prescribed motion; no learned policy or grasp evaluation'),
    ('fixed wrist mount; captures share one state',
     'two fixed wrist mounts; captures share one state'),
    ('"hand_from_camera": mount.tolist(),',
     '"hand_from_camera": mount.tolist(), "hand_from_camera_reference": "baseline",\n'
     '          "camera_labels": labels,\n'
     '          "camera_delta_in_baseline_optical_frame": shift.tolist(),\n'
     '          "hand_from_cameras": [mount.tolist(), (mount @ shift).tolist()],\n'
     '          "base_script_sha256": "' + base_sha + '",'),
]
for old, new in shift_changes:
    if shift_source.count(old) != 1:
        raise RuntimeError("原始代码的版本不匹配，请把提示发给我检查。")
    shift_source = shift_source.replace(old, new, 1)

shift_run = shift_work / datetime.now(timezone.utc).strftime("shift_x5cm_%Y%m%dT%H%M%S_%fZ")
shift_run.mkdir()
shift_script = shift_run / "demo.py"
shift_script.write_text(shift_source, encoding="utf-8")
(shift_run / "derivation.json").write_text(json.dumps({
    "base_run_directory": base_script.parent.name,
    "base_script_sha256": base_sha,
    "derived_script_sha256": hashlib.sha256(shift_script.read_bytes()).hexdigest(),
    "change": "Compare baseline wrist with baseline wrist @ Tx(0.05 m); same orientation. "
              "Scene, controls, physics steps, projection and frame timing are unchanged.",
}, indent=2), encoding="utf-8")

print("1/2 正在生成对照：左边原始手腕相机，右边横向偏移 5 厘米……", flush=True)
subprocess.run([str(shift_python), str(shift_script)], check=True)
gif_b64 = base64.b64encode((shift_run / "comparison.gif").read_bytes()).decode("ascii")
display(HTML(f'<img src="data:image/gif;base64,{gif_b64}" style="max-width:100%;height:auto;">'))
print("2/2 完成。重点看：右图中的方块，相比左图往哪边移动了？")
print("本次结果目录：", shift_run)
shift_zip = shutil.make_archive(str(shift_run), "zip", root_dir=str(shift_run))
print("已打包本次动图、截图、代码和记录：", Path(shift_zip).name)
files.download(shift_zip)
