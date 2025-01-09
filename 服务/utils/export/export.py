from io import BytesIO
import datetime
from collections import OrderedDict,defaultdict
import xlsxwriter
from CoilDataBase.models import SecondaryCoil, CoilDefect
from export_database import get_item_data, get_defects
import Globs
from CoilDataBase import Coil
from .export_config import ExportConfig

try:
    from export_image import export_image
except:
    from .export_image import export_image

def export_info_data(coil_id_list, workbook,export_config:ExportConfig=None):
    data_all = []
    key_list = []
    worksheet = workbook.add_worksheet(export_config.worksheet_name)
    for secondaryCoil in coil_id_list:
        item_dict = get_item_data(secondaryCoil,export_config)
        data_all.append(item_dict)
        if len(item_dict.keys()) > len(key_list):
            key_list = item_dict.keys()
    data = [key_list]
    for itemData in data_all:
        row=[]
        for key in key_list:
            try:
                row.append(itemData[key])
            except (Exception,) as e:
                row.append("")
        data.append(row)
  # 写入数据
    for row_num, row_data in enumerate(data):
        worksheet.write_row(row_num, 0, row_data)
    # 添加表格格式
    worksheet.add_table(
        0, 0, len(data) - 1, len(data[0]) - 1,  # 表格的范围
        {
            "columns": [{"header": col} for col in data[0]],  # 设置表头
            "style": "Table Style Medium 9",  # 表格样式
            "autofilter": True,  # 启用自动筛选
        }
    )
    return data_all


def export_defect_image(coil_id_list, workbook,export_config:ExportConfig=None):

    worksheet = workbook.add_worksheet(export_config.worksheet_defect_image_name)
    for secondaryCoil in coil_id_list:
        defects = get_defects(secondaryCoil)
        for defect in defects:
            defect:CoilDefect



def export_data_by_coil_id_list(coil_id_list, workbook, export_type="3D"):
    export_config = ExportConfig()

    if export_config.export_info:
        export_info_data(coil_id_list, workbook,export_config)

    if export_config.export_defect_image:
        export_defect_image(coil_id_list, workbook,export_config)


def export_data_by_time(start_time, end_time, export_type="3D"):
    output = BytesIO()
    # 将 BytesIO 对象传递给 xlsxwriter.Workbook
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    secondary_coil_list = Coil.getAllJoinDataByTime(start_time, end_time)
    export_data_by_coil_id_list(secondary_coil_list, workbook, export_type)
    workbook.close()
    file_size = output.getbuffer().nbytes
    # 重置 BytesIO 对象的读取位置
    output.seek(0)
    return output,file_size


def export_data_simple(num=50, max_coil=None, export_type="3D"):
    secondary_coil_list =  Coil.getAllJoinDataByNum(num, max_coil)

    workbook = xlsxwriter.Workbook("../数据导出测试.xlsx")
    data =  export_data_by_coil_id_list(secondary_coil_list, workbook, export_type)

    worksheet = workbook.add_worksheet("检出预览")
    export_image(data,worksheet)



if __name__ == '__main__':
    print(export_data_simple(40000, 40400, export_type="defect"))