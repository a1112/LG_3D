from PIL import Image

def join_image(images,ora="H", scale=1):
    if not (scale == 1):
        for i in range(len(images)):
            size = images[i].size
            images[i] = images[i].resize((int(size[0] * scale), int(size[1] * scale)))
    if ora == "H":
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths)
        max_height = max(heights)
        new_img = Image.new('L', (total_width, max_height))

        # 粘贴图像
        x_offset = 0
        for img in images:
            new_img.paste(img, (x_offset, 0))
            x_offset += img.size[0]
        return new_img
    else:
        widths, heights = zip(*(i.size for i in images))
        total_width = max(widths)
        max_height = sum(heights)
        new_img = Image.new('L', (total_width,max_height))
        # 粘贴图像
        y_offset = 0
        for img in images:
            new_img.paste(img, (0, y_offset))
            y_offset += img.size[1]
        return new_img