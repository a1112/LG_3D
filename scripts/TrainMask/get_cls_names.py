from pathlib import Path

print([folder.name for folder in Path(fr"F:\subImage\cropped_images").iterdir()])