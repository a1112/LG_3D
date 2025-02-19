from pathlib import Path

print(str([folder.name for folder in Path(fr"D:\CONFIG_3D\train\train").iterdir()]).replace("'",'"'))
