import time
from pathlib import WindowsPath

import numpy as np
import torch
from PIL import Image
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from timm.models import create_model


class CoilClsModel:
    def __init__(self,model_name="mobilenetv4_conv_aa_large.e230_r448_in12k_ft_in1k",
                 checkpoint_path=r'model/mobilenetv4.pth.tar'):
        self.model = create_model(model_name, checkpoint_path=checkpoint_path, num_classes=None, in_chans=3)
        self.model.eval()
        self.device = 'cuda:0'
        self.model = self.model.cuda()
        self.config = resolve_data_config({
        }, model=self.model)
        self.transform = create_transform(**self.config)

    def ImageToTensor(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        return self.transform(image.convert('RGB'))

    def predictImage(self, imageList, bach_size=32):
        res_index,res_source = [],[]
        imageCache: torch.Tensor = torch.Tensor().to(self.device)
        for index, img_ in list(enumerate(imageList)):
            if isinstance(imageList, (str, WindowsPath)):
                img_ = Image.open(imageList)
            tensor = self.ImageToTensor(img_)
            tensor = tensor.to(self.device)
            imageCache = torch.cat([imageCache, tensor[None]])
            if imageCache.shape[0] < bach_size and index < len(imageList) - 1:
                pass
            else:
                with torch.no_grad():
                    pred_resultsList = self.model(imageCache)
                    for out in pred_resultsList:
                        ls = list(torch.nn.functional.softmax(out, dim=0).cpu().numpy())
                        res_index.append(ls.index(max(ls)))
                        res_source.append(max(ls))
                imageCache: torch.Tensor = torch.Tensor().to('cuda:0')
        return res_index,res_source


ccm = CoilClsModel()

if __name__ == "__main__":
    st = time.time()
    r = ccm.predictImage([Image.open(r"E:\clfData\test\边部背景\92537_0.655604_14.jpg")]*100)
    et = time.time()
    print(et-st)
#     p = r"E:\clfData\r5\r5_cls_输出"
#     p2 = Path(r"E:\clfData\data")
#     classList = [f.name for f in Path(p2).glob("*")]
#     rootFolder = Path(p)
#     outFolder = rootFolder.parent / (rootFolder.name + "_cls_输出")
#     outFolder.mkdir(exist_ok=True, parents=True)
#     nameCache = []
#     imageCache = []
#
#     move=True
#
#     if move:
#         file_func= shutil.move
#     else:
#         file_func = shutil.copy
#     for jpg__ in tqdm(getAllImage(rootFolder)):
#         nameCache.append(jpg__)
#         imageCache.append(Image.open(jpg__))
#         if len(imageCache) < 64:
#             continue
#         dataList = predictImage(imageCache, bach_size=64)
#         for jpg_, data in zip(nameCache, dataList):
#             index = data.index(max(data))
#             source = str(data[index])[2]
#             if classList[index] == jpg_.parent.name:
#                 imageOutFolder = outFolder / "相同" / classList[index]
#                 okDict[classList[index]] += 1
#                 imageOutFolder.mkdir(exist_ok=True, parents=True)
#                 try:
#                     file_func(str(jpg_), str(imageOutFolder))
#                 except BaseException as e:
#                     print(e)
#             else:
#                 errorDict[classList[index]] += 1
#                 imageOutFolder = outFolder / "不同" / jpg_.parent.name / classList[index]
#                 imageOutFolder.mkdir(exist_ok=True, parents=True)
#                 try:
#                     file_func(str(jpg_), str(imageOutFolder))
#                 except BaseException as e:
#                     print(e)
#         imageCache = []
#         nameCache = []
#     okCount = 0
#     errorCount = 0
#     for k in classList:
#         print(f" {k} : {okDict[str(k)] / (okDict[str(k)] + errorDict[str(k)])}")
#         okCount += okDict[str(k)]
#         errorCount += errorDict[str(k)]
