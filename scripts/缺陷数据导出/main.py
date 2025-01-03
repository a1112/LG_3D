from pathlib import Path

import xlsxwriter
from PIL import Image, ImageDraw, ImageFont
import io
from CoilDataBase.config import Config,DeriverList
import requests
offline_mode=True

if offline_mode:
    Config.deriver = DeriverList.sqlite
    Config.file_url = fr"D:\CONFIG_3D\Coil.db"

from CoilDataBase import Coil, models


def create_sample_image():
    # 创建一个白色背景的图像
    img = Image.new('RGB', (200, 100), color='black')
    draw = ImageDraw.Draw(img)

    # 添加一些文本
    try:
        # 尝试加载一个字体
        font = ImageFont.truetype("arial.ttf", 15)
    except IOError:
        # 如果无法加载字体，使用默认字体
        font = ImageFont.load_default()

    return img

def insert_image_to_excel(image, excel_path):
    # 将PIL图像保存到字节流中，而不是磁盘
    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_stream.seek(0)  # 将指针移到开头

    # 创建一个新的Excel工作簿和工作表
    workbook = xlsxwriter.Workbook(excel_path)
    worksheet = workbook.add_worksheet()
    # 设置行高和列宽（根据需要调整）
    worksheet.set_row(0, 100)  # 设置第一行的高度
    worksheet.set_column('A:A', 30)  # 设置A列的宽度
    worksheet.insert_image('A1', 'image.png', {'image_data': image_stream, 'x_scale': 1, 'y_scale': 1})
    # 关闭工作簿以保存文件
    workbook.close()

class ExportDefect(object):
    def __init__(self, excel_path):
        self.export_type = "excel"
        if self.export_type == "excel":
            self.excel_path=Path(excel_path).with_suffix(".xlsx")

def get_database_data(from_coil_id,to_coil_id):
    return Coil.searchByCoilId(from_coil_id,to_coil_id)

def create_headers(worksheet):
    headers = ['流水号', '卷号', '钢种', '去向', '外径',"卷宽","卷厚","时间","缺陷"]
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

def export_defect_excel(excel_path,from_coil_id,to_coil_id):
    worksheet_title = "缺陷数据"
    workbook = xlsxwriter.Workbook(excel_path)
    worksheet = workbook.add_worksheet(worksheet_title)
    create_headers(worksheet)
    data = get_database_data(from_coil_id,to_coil_id)

def export_defect_excel_test():
    # export_defect_excel('defect_test.xlsx')
    print(get_database_data(10000,12000))
def create_table(worksheet):
    # 定义表头
    headers = ['编号', '姓名', '年龄', '部门', '薪资']
    # 写入表头
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

    # 写入数据
    for row_num, row_data in enumerate(data, start=1):
        for col_num, cell_data in enumerate(row_data):
            worksheet.write(row_num, col_num, cell_data)
    worksheet.set_column('A:E', 15)
    # # 定义表格区域
    # (max_row, max_col) = (len(data), len(headers) - 1)
    # table_range = f'A1:{xlsxwriter.utility.xl_col_to_name(max_col)}{max_row + 1}'
    #
    # # 添加表格
    # worksheet.add_table(table_range, {
    #     'columns': [
    #         {'header': '编号'},
    #         {'header': '姓名'},
    #         {'header': '年龄'},
    #         {'header': '部门'},
    #         {'header': '薪资'},
    #     ],
    #     'style': 'Table Style Medium 9'
    # })
    # 设置列宽
    # # 关闭工作簿以保存文件
    # workbook.close()
    # print(f"Excel文件已创建：{excel_file}")



if __name__ == "__main__":
    export_defect_excel_test()
