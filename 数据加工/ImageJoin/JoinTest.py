from pathlib import Path
import json
from PIL import Image

rootFolder = Path("cops/cops")
im_size = [1280,1024]
im_crop = [90,0,1100,1024]

imageMap = {}
for index, folder in enumerate(["Cap_L_U", "Cap_L_M", "Cap_L_D"]):
    folderPath = rootFolder / folder / "1640" / "2d"
    print(folderPath)
    imagePaths = folderPath.glob("*.bmp")
    imagePaths = sorted(imagePaths, key=lambda x: int(x.stem))
    for imagePath in imagePaths:
        if index not in imageMap:
            imageMap[index] = {}
        im = Image.open(str(imagePath))
        im = im.resize((im_size[0], im_size[1]))
        im = im.crop(im_crop)
        imageMap[index][imagePath.stem] = im
print(imageMap)
lineImageList=[]
for imageIndex, image in imageMap.items():
    lineImage = Image.new('L', (im_crop[2]-im_crop[0], len(image) * im_size[1]))
    for index, (imageName, im) in enumerate(image.items()):
        lineImage.paste(im, (0,index*im_size[1]))
    lineImageList.append(lineImage)
w1 = lineImageList[0].width
h1 = lineImageList[0].height
lineImageList[0] = lineImageList[0].crop((0,750,lineImageList[0].width,lineImageList[0].height-350))
lineImageList[0] = lineImageList[0].resize((w1, h1))
new_join_image = Image.new('L', ((im_crop[2]-im_crop[0])*len(lineImageList), lineImageList[1].height))
for index, lineImage in enumerate(lineImageList):
    new_join_image.paste(lineImage, (index*(im_crop[2]-im_crop[0]),0))
new_join_image = new_join_image.resize((new_join_image.width,int(new_join_image.height*0.4)))
new_join_image.show()
