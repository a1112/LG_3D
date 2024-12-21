from PIL import Image
import os

def convert_png_to_jpg(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            try:
                if file.lower().endswith(".jpg"):
                    png_path = os.path.join(root, file)
                    jpg_path = os.path.splitext(png_path)[0] + ".png"
                    img = Image.open(png_path)
                    img = img.convert("L")
                    img.save(jpg_path)
                    os.remove(png_path)
            except:
                pass

convert_png_to_jpg(rf"F:\ALG\SegTrainTest\trainTest\dataList\SaveMask")
