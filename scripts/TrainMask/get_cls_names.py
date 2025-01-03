from pathlib import Path

print([folder.name for folder in Path(fr"E:\train\cropped_images\cropped_images").iterdir()])