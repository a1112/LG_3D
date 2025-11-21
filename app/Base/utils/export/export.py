from io import BytesIO
import xlsxwriter

from Base.utils.export.export_image import export_defect_show_image, export_defect_un_show_image
from .export_database import export_info_data
from CoilDataBase import Coil
from .export_config import ExportConfig,XlsxWriterFormatConfig
from api.Models import ExportXlsxConfigModel

def export_data_by_coil_id_list(coil_id_list, workbook, export_type="3D",export_config:ExportXlsxConfigModel=None):
    export_config = ExportConfig(export_config)
    format_ = XlsxWriterFormatConfig(workbook)
    if export_config.export_info:
        export_info_data(coil_id_list, workbook, export_config,format_)

    if export_config.export_defect_image:
        # 数据导出
        if export_config.defect_show_info:
            export_defect_show_image(coil_id_list, workbook, export_config,format_)
        if export_config.defect_un_show_info:
            export_defect_un_show_image(coil_id_list, workbook, export_config, format_)



def export_data_by_coil_id(start_id, end_id, export_type="3D",export_config=None):
    output = BytesIO()
    # 将 BytesIO 对象传递给 xlsxwriter.Workbook
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    print("get_all_join_data_by_id")
    secondary_coil_list = Coil.get_all_join_data_by_id(start_id, end_id)
    export_data_by_coil_id_list(secondary_coil_list, workbook, export_type, export_config=export_config)
    workbook.close()
    # 重置 BytesIO 对象的读取位置
    output.seek(0)
    return output,output.getbuffer().nbytes

def export_data_by_time(start_time, end_time, export_type="3D", export_config:ExportXlsxConfigModel=None):
    output = BytesIO()
    # 将 BytesIO 对象传递给 xlsxwriter.Workbook
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    secondary_coil_list = Coil.get_all_join_data_by_time(start_time, end_time)
    export_data_by_coil_id_list(secondary_coil_list, workbook, export_type, export_config=export_config)
    workbook.close()
    file_size = output.getbuffer().nbytes
    # 重置 BytesIO 对象的读取位置
    output.seek(0)
    return output,file_size


def export_data_simple(num=50, max_coil=None, export_type="3D"):
    secondary_coil_list =  Coil.get_all_join_data_by_num(num, max_coil)

    workbook = xlsxwriter.Workbook("../数据导出测试.xlsx")

    export_data_by_coil_id_list(secondary_coil_list, workbook, export_type)


def export_data_by_config(config:ExportXlsxConfigModel):
    return export_data_by_time(config.startData,config.endData,config.export_type,config)

if __name__ == '__main__':
    print(export_data_simple(40000, 40400, export_type="defect"))