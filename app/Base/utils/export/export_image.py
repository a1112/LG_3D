#  数据导出
import io
from pathlib import Path

from CoilDataBase.models import CoilDefect, SecondaryCoil

from Base import CONFIG
from Base.CONFIG import serverConfigProperty
from .export_config import ExportConfig, XlsxWriterFormatConfig
from .export_database import get_defects, get_header_data
from  Base.tools.DataGet import get_pil_image_by_defect


def get_pil_image_from_classifier_save(defect: CoilDefect):
    """
    从 classifier 目录获取缺陷图像

    优先级顺序：
    1. 卷材级 classifier 文件夹：D:\Save_S\{coil_id}\classifier\{defect_name}\{coil_id}_{x}_{y}_{w}_{h}.png
    2. 全局 classifier_save 文件夹：classifier_save/classifier/{defect_name}/{coil_id}_{x}_{y}_{w}_{h}.png
    3. 原始图像裁剪（最后备选）

    Args:
        defect: 缺陷对象

    Returns:
        PIL.Image or None: 缺陷图像，如果找不到则返回 None
    """
    from PIL import Image

    try:
        # 获取基础目录
        save_folder = list(serverConfigProperty.surfaceConfigPropertyDict.values())[0].saveFolder
        save_base = Path(save_folder).parent  # D:\Save_S

        coil_id = defect.secondaryCoilId
        coil_folder = save_base / str(coil_id)  # D:\Save_S\{coil_id}

        # 构建文件名：coil_id_x_y_w_h.png
        x1 = int(defect.defectX)
        y1 = int(defect.defectY)
        x2 = x1 + int(defect.defectW)
        y2 = y1 + int(defect.defectH)

        # 尝试多个可能的文件名格式
        possible_names = [
            f"{coil_id}_{x1}_{y1}_{x2}_{y2}.png",  # xmin_ymin_xmax_ymax
            f"{coil_id}_{x1}_{y1}_{int(defect.defectW)}_{int(defect.defectH)}.png",  # x_y_w_h
        ]

        # 标准化缺陷名称（去掉后缀数字，如 "背景(1)" -> "背景"）
        defect_name = defect.defectName
        if defect_name.endswith(")"):
            defect_name = defect_name.split("(")[0].rstrip()

        # 优先级1：检查卷材级 classifier 文件夹 D:\Save_S\{coil_id}\classifier\{defect_name}\
        coil_classifier_path = coil_folder / "classifier" / defect_name
        if coil_classifier_path.exists():
            for name in possible_names:
                image_path = coil_classifier_path / name
                if image_path.exists():
                    return Image.open(image_path)

        # 优先级2：检查全局 classifier_save 文件夹
        classifier_save_base = save_base / "classifier_save"
        global_classifier_path = classifier_save_base / "classifier" / defect_name
        if global_classifier_path.exists():
            for name in possible_names:
                image_path = global_classifier_path / name
                if image_path.exists():
                    return Image.open(image_path)

        # 优先级3：检查其他可能的 classifier 路径（例如 Save_L 等）
        for surface_key in ["S", "L"]:
            surface_folder = save_base / f"Save_{surface_key}"
            if surface_folder.exists():
                coil_path = surface_folder / str(coil_id) / "classifier" / defect_name
                if coil_path.exists():
                    for name in possible_names:
                        image_path = coil_path / name
                        if image_path.exists():
                            return Image.open(image_path)

        # 所有路径都找不到，返回 None（不回退到原始裁剪）
        print(f"Warning: Image not found for defect {defect.defectName} in coil {coil_id}")
        return None

    except Exception as e:
        print(f"Error loading from classifier: {e}")
        return None


def get_item_data(secondary_coil:SecondaryCoil,export_config:ExportConfig=None):
    res_data={}
    alarm_info_dict={"S":None,"L":None}
    defects = get_defects(secondary_coil)

    if export_config.export_header_data:
        res_data.update(get_header_data(secondary_coil))   # 添加 二级数据信息
    # if len(defects) <= 0:
    #     return res_data
    res_data.update({
        "defects":defects
    })
    # alarm_info_list = secondary_coil.childrenAlarmInfo
    # for alarm_info in alarm_info_list:
    #     alarm_info_dict[alarm_info.surface]=alarm_info
    return res_data

def export_defect_image_by_names(coil_id_list, worksheet, export_config:ExportConfig=None, names=None,in_list=True,format_=None):
    if names is None:
        names = []
    data_all = []
    head_key_list = []
    skipped_images = []  # 记录跳过的图像
    print(f"coil_id_list: {len(coil_id_list)}")
    for secondaryCoil in coil_id_list:
        item_dict = get_item_data(secondaryCoil,export_config)
        if item_dict is None:
            continue

        data_all.append(item_dict)
        if len(item_dict.keys()) > len(head_key_list):
            head_key_list = list(item_dict.keys())

    data = [head_key_list]
    for itemData in data_all:
        row=[]
        for key in head_key_list:
            try:
                row.append(itemData[key])
            except (Exception,) as e:
                row.append("")
        data.append(row)

    for row_num, row_data in enumerate(data):
        if row_num==0:
            worksheet.write_row(row_num, 0, row_data)
            continue

        defects = row_data[-1]
        text_row = row_data[:-1]
        for index,data_item in enumerate(text_row):
            worksheet.write(row_num, index, data_item)
        offset=len(row_data)
        for index, defect in enumerate(defects):
            defect.defectName = CONFIG.defectClassesProperty.format_name(defect.defectName)
            if in_list:
                if defect.defectName not in names:
                    continue
            else:
                if defect.defectName in names:
                    continue

            image = get_pil_image_from_classifier_save(defect)
            # 失败跳过逻辑：如果图像加载失败，跳过该缺陷
            if image is None:
                skipped_images.append({
                    'coil_id': defect.secondaryCoilId,
                    'defect_name': defect.defectName,
                    'x': defect.defectX,
                    'y': defect.defectY
                })
                continue

            defect:CoilDefect
            text = f"{defect.defectName}\n宽：{int((defect.defectW*0.34))}\n高：{int(defect.defectH*0.34)}"
            insert_image_and_name(worksheet,row_num, offset,text, image,format_)
            offset+=2

    # 输出跳过的图像统计
    if skipped_images:
        print(f"Warning: Skipped {len(skipped_images)} defect images due to loading errors")
        for item in skipped_images[:5]:  # 只打印前5个
            print(f"  - Coil {item['coil_id']}: {item['defect_name']} at ({item['x']}, {item['y']})")
        if len(skipped_images) > 5:
            print(f"  ... and {len(skipped_images) - 5} more")

def export_defect_show_image(coil_id_list, workbook,export_config:ExportConfig=None,format_=None):

    worksheet = workbook.add_worksheet(export_config.worksheet_defect_image_name+"_显示")
    export_defect_image_by_names(coil_id_list, worksheet, export_config, CONFIG.defectClassesProperty.show_name_list, format_=format_)

def export_defect_un_show_image(coil_id_list, workbook,export_config:ExportConfig=None,format_=None):
    worksheet = workbook.add_worksheet(export_config.worksheet_defect_image_name + "_屏蔽")
    export_defect_image_by_names(coil_id_list, worksheet, export_config, CONFIG.defectClassesProperty.show_name_list,
                                 False, format_=format_)


def insert_image_and_name(worksheet, row_num, index,text, image,format_:XlsxWriterFormatConfig):
    worksheet.set_row(row_num, 150)  # 设置第一行的高度
    worksheet.set_column(index+1,index+1, 25)  # 设置A列的宽度
    # 设置单元格格式，使其支持自动换行
    worksheet.write(row_num, index, text,format_.cell_format)


    new_size = 150
    # Get the original width and height
    width, height = image.size
    if width>new_size or height>new_size:
        # Calculate the scaling factor
        scaling_factor = min(new_size / width, new_size / height)
        # Calculate the new dimensions
        new_width = int(width * scaling_factor)
        new_height = int(height * scaling_factor)
        # Resize the image
        image = image.resize((new_width, new_height))

    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_stream.seek(0)  # 将指针移到开头
    worksheet.insert_image(row_num, index+1, 'image.png', {'image_data': image_stream, 'x_scale': 1, 'y_scale': 1})
    # 添加表格格式
    # worksheet.add_table(
    #     0, 0, len(data) - 1, len(data[0]) - 1,  # 表格的范围
    #     {
    #         "columns": [{"header": col} for col in data[0]],  # 设置表头
    #         "style": "Table Style Medium 9",  # 表格样式
    #         "autofilter": True,  # 启用自动筛选
    #     }
    # )