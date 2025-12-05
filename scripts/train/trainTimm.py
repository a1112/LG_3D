import json
from pathlib import Path

# 训练输出统一写入 CONFIG_3D/model/classifier/classifier.json，供运行时 CoilClsModel 使用
configSave = Path(r"D:\CONFIG_3D\model\classifier") / "classifier.json"
configSave.parent.mkdir(parents=True, exist_ok=True)
train_folder = Path(fr"E:\train\cropped_images")
train_split = "cropped_images"
val_split = "cropped_images"
model_name = "mobilenetv4_conv_small"
save_checkpoint_path = f"model/{model_name}.tar"
in_chans = 3
amp = True
names = [f_.name for f_ in (train_folder / train_split).iterdir()]
print(names)
with configSave.open("w", encoding="utf-8") as f:
    json.dump(
        {
            "model_name": model_name,
            "checkpoint_path": save_checkpoint_path,
            "in_chans": in_chans,
            "names": names
        }
        , f, ensure_ascii=False, indent=4)
