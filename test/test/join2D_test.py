from pathlib import Path

from PIL import Image


def horizontal_concat(images):
    """
    水平拼接多个图像
    :param images: 图像路径列表或Image对象列表
    :return: 拼接后的图像
    """

    if not images:
        raise ValueError("at least one image is required")

    imgs = []
    for image in images:
        if isinstance(image, (str, Path)):
            with Image.open(image) as source:
                image = source.copy()
        width, height = image.size
        if width <= 2400:
            raise ValueError(f"image width must be greater than 2400: {width}")
        imgs.append(image.crop([1200, 0, width - 1200, height]))

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


def main():
    test_folder = Path(r"G:\Cap_S_U\62302\area")
    image_paths = sorted(
        test_folder.glob("*.jpg"),
        key=lambda path: int(path.stem),
        reverse=True,
    )
    if not image_paths:
        raise FileNotFoundError(f"no JPG images found in {test_folder}")
    new_image = horizontal_concat(image_paths)
    new_image.save("test.jpg")


if __name__ == "__main__":
    main()
