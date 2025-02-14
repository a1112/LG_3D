from api.Models import ExportXlsxConfigModel


class ExportConfig:
    def __init__(self,export_config:ExportXlsxConfigModel=None):
        self.export_config=export_config

        self.export_info = True

        self.export_path = None
        self.export_header_data = True      # 导出
        self.worksheet_name = self.get("data_worksheet_name","数据报表")
        self.worksheet_defect_image_name = self.get("defect_worksheet_name","缺陷识别")
        self.export_plc_data = False        # 导出 PLC 数据
        self.detection_3d_info=True
        self.export_alarm_info = True       # 导出报警
        self.export_taper_shape_info = True # 塔形数据导出
        self.export_alarm_loose = True      # 导出松卷 数据
        self.export_defect_data = True      # 导出缺陷数据
        self.defect_show_info = True
        self.defect_un_show_info = True

        self.export_defect_image = True     # 导出 缺陷小图
        if self.export_config:
            self.export_plc_data = self.export_config.export_plc_data
            self.detection_3d_info = self.export_config.detection_3d_info
            self.export_defect_data = self.export_config.defect_info
            self.defect_show_info = self.export_config.defect_show_info
            self.defect_un_show_info=self.export_config.defect_un_show_info




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
