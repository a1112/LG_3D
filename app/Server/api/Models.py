from typing import Optional, Any

from pydantic import BaseModel



class ExportXlsxConfigModel(BaseModel):
    export_type: str
    detection_3d_info:bool
    defect_info:bool
    defect_show_info:bool
    defect_un_show_info:bool
    export_plc_data:bool
    startDate:str
    endDate:str
    # {'export_type': 'xlsx', 'detection_3d_info': True, 'defect_info': True, 'defect_show_info': True,
    #  'defect_un_show_info': False, 'export_plc_data': False, 'startDate': '202502121742', 'endDate': '202502141347'}
    # def __init__(self, **data: Any):
    #     super().__init__(**data)
