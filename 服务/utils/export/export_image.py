#  数据导出
import io

from CoilDataBase.models import CoilDefect, SecondaryCoil

import CONFIG
import Globs
from .export_config import ExportConfig, XlsxWriterFormatConfig
from .export_database import get_defects, get_header_data
from  tools.DataGet import get_pil_image_by_defect


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

            image = get_pil_image_by_defect(defect)
            defect:CoilDefect
            text = f"{defect.defectName}\n宽：{int((defect.defectW*0.34))}\n高：{int(defect.defectH*0.34)}"
            insert_image_and_name(worksheet,row_num, offset,text, image,format_)
            offset+=2

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