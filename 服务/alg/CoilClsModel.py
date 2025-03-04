import json
import time
from pathlib import WindowsPath

import numpy as np
import torch
from PIL import Image
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from timm.models import create_model
from CONFIG import get_file_url, coilClassifiersConfigFile


class CoilClsModel:
    def __init__(self, model_name=None,
                 checkpoint_path=None, in_chans=3, config=None):
        self.model_name = model_name
        self.checkpoint_path = checkpoint_path
        self.in_chans = in_chans
        if model_name is None and config is None:
            config = coilClassifiersConfigFile
        self.names = []
        if config is not None:
            config = json.load(open(config, encoding="utf-8"))
            self.model_name = config["model_name"]
            self.checkpoint_path = get_file_url(config["checkpoint_path"])
            self.in_chans = config["in_chans"]
            self.names = config["names"]

        self.model = create_model(self.model_name, checkpoint_path=self.checkpoint_path, num_classes=None, in_chans=self.in_chans)
        self.model.eval()
        self.device = 'cuda:0'
        self.model = self.model.cuda()
        self.config = resolve_data_config({
        }, model=self.model)
        if self.in_chans==1:
            self.config["input_size"]=(1,224,224)
            self.config["mean"]=(0.485,)
            self.config["std"]=(0.229, )
        print(self.config)
        self.transform = create_transform(**self.config)

    def image_to_tensor(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        if self.in_chans == 1:
            return self.transform(image)
        return self.transform(image.convert('RGB'))

    def predict_image(self, image_list, bach_size=32):
        res_index, res_source, names = [], [], []
        image_cache: torch.Tensor = torch.Tensor().to(self.device)
        for index, img_ in list(enumerate(image_list)):
            if isinstance(img_, (str, WindowsPath)):
                try:
                    img_ = Image.open(img_)
                except BaseException as e:
                    print(e)
                    continue
            tensor = self.image_to_tensor(img_)
            tensor = tensor.to(self.device)
            image_cache = torch.cat([image_cache, tensor[None]])
            if image_cache.shape[0] < bach_size and index < len(image_list) - 1:
                pass
            else:
                with torch.no_grad():
                    pred_results_list = self.model(image_cache)
                    for out in pred_results_list:
                        ls = list(torch.nn.functional.softmax(out, dim=0).cpu().numpy())
                        index = ls.index(max(ls))
                        res_index.append(index)
                        res_source.append(float(max(ls)))
                        names.append(self.names[index])
                image_cache: torch.Tensor = torch.Tensor().to('cuda:0')
        return res_index, res_source, names


if __name__ == "__main__":
    st = time.time()
    ccm = CoilClsModel()

    r = ccm.predict_image([Image.open(r"E:\clfData\test\边部背景\92537_0.655604_14.jpg")] * 100)
    et = time.time()
    print(et - st)
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
