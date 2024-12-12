import io
from property.ServerConfigProperty import ServerConfigProperty
from api.ApiCache import previewCache, imageCache,_3dDataCache
from Globs import serverConfigProperty

serverConfigProperty:ServerConfigProperty

from PIL import Image, ImageDraw, ImageFont

# 创建带有白色背景的图像
width, height = 150, 150
image = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(image)

# 加载字体
font = ImageFont.load_default(30)

# 要添加的文本
text = "Not Found"

bbox = draw.textbbox((0, 0), text, font=font)
text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
position = ((width - text_width) / 2, (height - text_height) / 2)
# 在图像上添加文本
draw.text(position, text, fill="black", font=font)
img_byte_arr = io.BytesIO()
image.save(img_byte_arr, format='jpeg')
img_byte_arr.seek(0)
noFindImageByte = img_byte_arr.getvalue()


class DataGet:
    def __init__(self, source_type, surface_key, coil_id, type_, mask):
        self.sourceType = source_type
        self.surfaceKey = surface_key
        self.coil_id = coil_id
        self.type_ = type_
        self.mask = mask

    def get_source(self):
        if self.sourceType == "preview":
            url = serverConfigProperty.get_preview_file(self.coil_id, self.surfaceKey, self.type_)
        else:
            url = serverConfigProperty.get_file(self.coil_id, self.surfaceKey, self.type_,self.mask)
        return url

    def get3d_source(self):
        return serverConfigProperty.get_3d_file(self.coil_id, self.surfaceKey)

    def get_mask_source(self):
        if self.sourceType == "preview":
            url = serverConfigProperty.get_preview_file(self.coil_id, self.surfaceKey, "MASK")
        else:
            url = serverConfigProperty.get_file(self.coil_id, self.surfaceKey, "MASK")
        return url

    def get_image(self):
        url = self.get_source()
        if self.sourceType == "preview":
            return previewCache.get_image(url)
        else:
            return imageCache.get_image(url)

    def get_3d_data(self):
        url = self.get3d_source()
        print(url)
        return _3dDataCache.get_data(url)

    def get_mesh_source(self):
        return serverConfigProperty.get_mesh_file(self.coil_id, self.surfaceKey)

    def get_mesh(self):
        return self.get_mesh_source()
