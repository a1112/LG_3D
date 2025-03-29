from pathlib import Path
from PIL import Image

testFolder = Path(fr"G:\Cap_S_U\62299\area")
image_url_list = list(testFolder.glob("*.jpg"))
image_url_list.sort(key=lambda i : int(Path(i).stem))
image_url_list = image_url_list[:][::-1]
image_list = [Image.open(u) for u in image_url_list]


def horizontal_concat(images):
    """
    水平拼接多个图像
    :param images: 图像路径列表或Image对象列表
    :return: 拼接后的图像
    """
    
    for i in range(len(images)):
        w, h = images[i].size
        images[i] = images[i].crop([1200, 0, w-1200, h])
    # 打开所有图像并转换为Image对象
    imgs = [Image.open(i) if isinstance(i, str) else i for i in images]

    # 计算总宽度和最大高度
    widths, heights = zip(*(i.size for i in imgs))
    total_width = sum(widths)
    max_height = max(heights)

    # 创建新图像
    new_img = Image.new('RGB', (total_width, max_height))

    # 粘贴图像
    x_offset = 0
    for img in imgs:
        new_img.paste(img, (x_offset, 0))
        x_offset += img.size[0]

    return new_img

newImage = horizontal_concat(image_list)
size = newImage.size
newImage = newImage.resize((int(size[0]*0.2),int(size[1]*0.2)))
newImage.show()