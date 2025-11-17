from PIL import Image
import os

def convert_png_to_jpg(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            try:
                if file.lower().endswith(".png"):
                    png_path = os.path.join(root, file)
                    jpg_path = os.path.splitext(png_path)[0] + ".jpg"
                    img = Image.open(png_path)
                    img = img.convert("L")
                    img.save(jpg_path)
                    os.remove(png_path)
            except:
                pass

root_dir = rf"G:\SaveMask\Cap_L_M"
convert_png_to_jpg(root_dir)
