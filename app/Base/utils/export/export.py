import logging
from io import BytesIO
from time import perf_counter

import xlsxwriter

from Base.utils.export.export_image import (
    export_3d_defect_image,
    export_area_2d_defect_image,
)
from .export_database import export_info_data
from CoilDataBase import Coil
from .export_config import ExportConfig, XlsxWriterFormatConfig
from api.Models import ExportXlsxConfigModel

logger = logging.getLogger(__name__)
DEFAULT_MAX_EXPORT_COILS = 5000
DEFAULT_MAX_EXPORT_DEFECTS = 20000


class ExportLimitExceeded(ValueError):
    """Raised before building an in-memory workbook for an oversized export."""

    def __init__(self, max_coils: int):
        self.max_coils = max_coils
        super().__init__(f"export contains more than {max_coils} coils")


class ExportDefectLimitExceeded(ValueError):
    """Raised before building a workbook with too many defect relationships."""

    def __init__(self, max_defects: int):
        self.max_defects = max_defects
        super().__init__(f"export contains more than {max_defects} defects")


def _write_empty_export_sheet(workbook, export_config: ExportConfig):
    worksheet = workbook.add_worksheet(export_config.worksheet_name[:31])
    worksheet.write(0, 0, "无导出数据")
    worksheet.write(1, 0, "当前导出时间范围内没有查询到卷材数据")


def export_data_by_coil_id_list(coil_id_list,
                                workbook,
                                export_type="3D",
                                export_config: ExportXlsxConfigModel = None):
    export_config = ExportConfig(export_config)
    if not coil_id_list:
        logger.warning("[Export] no coil data found for export")
        _write_empty_export_sheet(workbook, export_config)
        return

    format_ = XlsxWriterFormatConfig(workbook)
    logger.info(
        "[Export] start body coils=%s export_info=%s export_defect_image=%s export_area_defect_image=%s",
        len(coil_id_list),
        export_config.export_info,
        export_config.export_defect_image,
        export_config.export_area_defect_image,
    )
    if export_config.export_info:
        step_start = perf_counter()
        export_info_data(coil_id_list, workbook, export_config, format_)
        logger.info("[Export] info sheet done duration=%.3fs",
                    perf_counter() - step_start)

    if export_config.export_defect_image:
        # 数据导出
        logger.info(
            "[Export] export_defect_image=%s, defect_show_info=%s, defect_un_show_info=%s",
            export_config.export_defect_image,
            export_config.defect_show_info,
            export_config.defect_un_show_info,
        )
        if export_config.defect_show_info or export_config.defect_un_show_info:
            logger.info("[Export] Calling export_3d_defect_image with %s coils", len(coil_id_list))
            step_start = perf_counter()
            export_3d_defect_image(coil_id_list, workbook, export_config,
                                   format_)
            logger.info("[Export] 3D defect image sheet done duration=%.3fs",
                        perf_counter() - step_start)
        if export_config.export_area_defect_image:
            logger.info("[Export] Calling export_area_2d_defect_image")
            step_start = perf_counter()
            export_area_2d_defect_image(coil_id_list, workbook, export_config,
                                        format_)
            logger.info("[Export] 2D defect image sheet done duration=%.3fs",
                        perf_counter() - step_start)


def export_data_by_coil_id(start_id,
                           end_id,
                           export_type="3D",
                           export_config=None,
                           max_defects: int = DEFAULT_MAX_EXPORT_DEFECTS):
    max_defects = max(int(max_defects), 1)
    try:
        secondary_coil_list = Coil.get_all_join_data_by_id(
            start_id,
            end_id,
            max_defects=max_defects,
        )
    except Coil.QueryDefectLimitExceeded as exc:
        raise ExportDefectLimitExceeded(max_defects) from exc
    output = BytesIO()
    # 将 BytesIO 对象传递给 xlsxwriter.Workbook
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    logger.debug("get_all_join_data_by_id")
    export_data_by_coil_id_list(secondary_coil_list,
                                workbook,
                                export_type,
                                export_config=export_config)
    workbook.close()
    # 重置 BytesIO 对象的读取位置
    output.seek(0)
    return output, output.getbuffer().nbytes


def export_data_by_time(start_time,
                        end_time,
                        export_type="3D",
                        export_config: ExportXlsxConfigModel = None,
                        max_coils: int = DEFAULT_MAX_EXPORT_COILS,
                        max_defects: int = DEFAULT_MAX_EXPORT_DEFECTS):
    total_start = perf_counter()
    max_coils = max(int(max_coils), 1)
    max_defects = max(int(max_defects), 1)
    query_start = perf_counter()
    try:
        secondary_coil_list = Coil.get_all_join_data_by_time(
            start_time,
            end_time,
            max_count=max_coils,
            max_defects=max_defects,
        )
    except Coil.QueryResultLimitExceeded as exc:
        raise ExportLimitExceeded(max_coils) from exc
    except Coil.QueryDefectLimitExceeded as exc:
        raise ExportDefectLimitExceeded(max_defects) from exc
    # Keep the caller safe if a compatible database implementation accepts the
    # new keyword but returns an extra sentinel row instead of raising.
    if len(secondary_coil_list) > max_coils:
        raise ExportLimitExceeded(max_coils)
    logger.info(
        "[Export] query by time start=%s end=%s coils=%s duration=%.3fs",
        start_time,
        end_time,
        len(secondary_coil_list),
        perf_counter() - query_start,
    )
    # Allocate the in-memory XLSX only after the bounded database query passes.
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    body_start = perf_counter()
    export_data_by_coil_id_list(secondary_coil_list,
                                workbook,
                                export_type,
                                export_config=export_config)
    logger.info("[Export] workbook body done duration=%.3fs",
                perf_counter() - body_start)
    close_start = perf_counter()
    workbook.close()
    close_duration = perf_counter() - close_start
    file_size = output.getbuffer().nbytes
    # 重置 BytesIO 对象的读取位置
    output.seek(0)
    logger.info(
        "[Export] export_data_by_time done coils=%s file_size=%s close_duration=%.3fs total_duration=%.3fs",
        len(secondary_coil_list),
        file_size,
        close_duration,
        perf_counter() - total_start,
    )
    return output, file_size


def export_data_simple(num=50, max_coil=None, export_type="3D"):
    secondary_coil_list = Coil.get_all_join_data_by_num(num, max_coil)

    workbook = xlsxwriter.Workbook("../数据导出测试.xlsx")

    export_data_by_coil_id_list(secondary_coil_list, workbook, export_type)


def export_data_by_config(config: ExportXlsxConfigModel):
    return export_data_by_time(config.startData, config.endData,
                               config.export_type, config)


if __name__ == '__main__':
    logger.info(export_data_simple(40000, 40400, export_type="defect"))
