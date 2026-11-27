# 在刚才的 Colab 笔记本下方新增代码格，粘贴并运行。
from pathlib import Path
from IPython.display import HTML, display
from google.colab import files
import base64
import shutil

if "run" not in globals():
    raise RuntimeError("当前运行时没有保留结果变量，请先运行上面的机械臂演示代码格。")
run_dir = Path(run)
gif_data = base64.b64encode((run_dir / "comparison.gif").read_bytes()).decode("ascii")
display(HTML(f'<img src="data:image/gif;base64,{gif_data}" style="max-width:100%;height:auto;">'))

zip_path = shutil.make_archive(str(run_dir), "zip", root_dir=str(run_dir))
print("已打包本次动图、截图、代码和运行记录：", Path(zip_path).name)
files.download(zip_path)
