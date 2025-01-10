#  数据导出
import io

from CoilDataBase.models import CoilDefect, SecondaryCoil

from .export_config import ExportConfig
from .export_database import get_defects, get_header_data
from  tools.DataGet import get_pil_image_by_defect


def get_item_data(secondary_coil:SecondaryCoil,export_config:ExportConfig=None):
    res_data={}
    alarm_info_dict={"S":None,"L":None}
    defects = get_defects(secondary_coil)
    if len(defects) <= 0:
        return None
    if export_config.export_header_data:
        res_data.update(get_header_data(secondary_coil))   # 添加 二级数据信息
    res_data.update({
        "defects":defects
    })
    # alarm_info_list = secondary_coil.childrenAlarmInfo
    # for alarm_info in alarm_info_list:
    #     alarm_info_dict[alarm_info.surface]=alarm_info
    return res_data

def export_defect_image(coil_id_list, workbook,export_config:ExportConfig=None):
    print(f"coil_id_list: {len(coil_id_list)}")
    data_all = []
    head_key_list = []
    worksheet = workbook.add_worksheet(export_config.worksheet_defect_image_name)
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
            image = get_pil_image_by_defect(defect)
            image = image.resize([100,100])
            defect:CoilDefect
            insert_image_and_name(worksheet,row_num, offset,defect.defectName, image)
            offset+=2

def insert_image_and_name(worksheet, row_num, index,name, image):
    worksheet.set_row(row_num, 100)  # 设置第一行的高度
    worksheet.set_column(index+1, 100)  # 设置A列的宽度

    worksheet.write(row_num, index, name)

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