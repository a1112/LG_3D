

class ExportConfig:
    def __init__(self,export_config=None):
        self.export_config=export_config

        self.export_info = True
        self.export_path = None
        self.export_header_data = True      # 导出
        self.worksheet_name = self.get("data_worksheet_name","数据报表")
        self.worksheet_defect_image_name = self.get("defect_worksheet_name","缺陷识别")





        self.export_plc_data = False        # 导出 PLC 数据
        self.export_alarm_info = True       # 导出报警
        self.export_taper_shape_info = True # 塔形数据导出
        self.export_alarm_loose = True      # 导出松卷 数据
        self.export_defect_data = True      # 导出缺陷数据
        self.export_defect_image = True     # 导出 缺陷小图

    def get(self,key,default_value):
        if key in self.export_config:
            return self.export_config[key]
        print(f"export_config error key:{key}  default_value:{default_value}")
        return default_value


class XlsxWriterFormatConfig:

    def __init__(self,workbook):
        self.workbook = workbook
        self.cell_format = workbook.add_format({'text_wrap': True,
                                                'align': 'center',
                                                 'valign': 'vcenter'})
