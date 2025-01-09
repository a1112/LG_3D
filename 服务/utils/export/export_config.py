

class ExportConfig:
    def __init__(self):

        self.worksheet_name = "数据报表"
        self.worksheet_defect_image_name = "缺陷识别"

        self.export_info = True

        self.export_path = None
        self.export_header_data = True      # 导出
        self.export_plc_data = False        # 导出 PLC 数据
        self.export_alarm_info = True       # 导出报警
        self.export_taper_shape_info = True # 塔形数据导出
        self.export_alarm_loose = True      # 导出松卷 数据
        self.export_defect_data = True      # 导出缺陷数据

        self.export_defect_image = True     # 导出 缺陷小图