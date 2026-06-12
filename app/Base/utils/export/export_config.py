from api.Models import ExportXlsxConfigModel


class ExportConfig:

    def __init__(self, export_config: ExportXlsxConfigModel = None):
        self.export_config = export_config

        self.export_info = True
        self.export_path = None
        self.export_header_data = True
        self.worksheet_name = self.get("data_worksheet_name", "数据报表")
        self.worksheet_defect_image_name = self.get("defect_worksheet_name",
                                                    "缺陷识别")
        self.export_plc_data = False
        self.detection_3d_info = True
        self.export_alarm_info = True
        self.export_taper_shape_info = True
        self.export_alarm_loose = True
        self.export_defect_data = True
        self.defect_show_info = True
        self.defect_un_show_info = False
        self.export_defect_image = True
        self.export_area_defect_image = True

        if self.export_config:
            self.export_plc_data = self.export_config.export_plc_data
            self.detection_3d_info = self.export_config.detection_3d_info
            self.export_defect_data = self.export_config.defect_info
            self.defect_show_info = self.export_config.defect_show_info
            self.defect_un_show_info = self.export_config.defect_un_show_info
            self.export_area_defect_image = self.get("area_defect_image", True)
            # 确保图像导出始终启用
            self.export_defect_image = True

    def get(self, key, default_value):
        if self.export_config is None:
            return default_value
        if isinstance(self.export_config, dict):
            return self.export_config.get(key, default_value)
        if hasattr(self.export_config, key):
            return getattr(self.export_config, key)
        return default_value


class XlsxWriterFormatConfig:

    def __init__(self, workbook):
        self.workbook = workbook
        self.cell_format = workbook.add_format({
            "text_wrap": True,
            "align": "center",
            "valign": "vcenter",
        })
