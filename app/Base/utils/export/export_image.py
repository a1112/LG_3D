#  数据导出
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from CoilDataBase.models import CoilDefect, SecondaryCoil

from Base import CONFIG
from Base.CONFIG import serverConfigProperty
from .export_config import ExportConfig, XlsxWriterFormatConfig
from .export_database import get_defects, get_header_data
from Base.tools.DataGet import DataGet, get_pil_image
from Base.tools.tool import expansion_box


AREA_2D_DEFECT_CROP_MARGIN_PX = 40


def _defect_int(value, default=0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _defect_box_values(defect: CoilDefect) -> tuple[int, int, int, int, int, int]:
    x1 = _defect_int(getattr(defect, "defectX", 0))
    y1 = _defect_int(getattr(defect, "defectY", 0))
    w = _defect_int(getattr(defect, "defectW", 0))
    h = _defect_int(getattr(defect, "defectH", 0))
    return x1, y1, w, h, x1 + w, y1 + h


def _normalized_defect_name(defect_name: str) -> str:
    defect_name = str(defect_name or "")
    if defect_name.endswith(")") and "(" in defect_name:
        return defect_name.split("(")[0].rstrip()
    return defect_name


def _defect_name_candidates(defect: CoilDefect,
                            defect_name: str | None = None) -> list[str]:
    names = []
    for value in (defect_name, getattr(defect, "defectName", "")):
        name = str(value or "")
        for candidate in (name, _normalized_defect_name(name)):
            if candidate and candidate not in names:
                names.append(candidate)
    return names or ["Unknown"]


def _crop_margin_for_defect(defect: CoilDefect) -> int | None:
    if _is_2d_defect(defect):
        return AREA_2D_DEFECT_CROP_MARGIN_PX
    return None


def _classifier_file_names(defect: CoilDefect,
                           crop_margin: int | None = None) -> list[str]:
    coil_id = getattr(defect, "secondaryCoilId", "")
    x1, y1, w, h, x2, y2 = _defect_box_values(defect)
    suffix = "" if crop_margin is None else f"_m{crop_margin}"
    names = [
        f"{coil_id}_{x1}_{y1}_{x2}_{y2}{suffix}.png",
        f"{coil_id}_{x1}_{y1}_{w}_{h}{suffix}.png",
        f"{coil_id}_{x1}_{y1}_{x2}_{y2}{suffix}.jpg",
        f"{coil_id}_{x1}_{y1}_{w}_{h}{suffix}.jpg",
        f"{coil_id}_{x1}_{y1}_{x2}_{y2}{suffix}.jpeg",
        f"{coil_id}_{x1}_{y1}_{w}_{h}{suffix}.jpeg",
    ]
    return list(dict.fromkeys(names))


def _load_image_copy(image_path: Path):
    try:
        if image_path.exists() and image_path.is_file():
            with Image.open(image_path) as image:
                return image.copy()
    except Exception as e:
        print(f"[Export] failed to load saved defect image {image_path}: {e}")
    return None


def _iter_defect_data_values(value):
    if value is None:
        return
    if isinstance(value, dict):
        for key in (
                "image_path",
                "imagePath",
                "path",
                "file",
                "url",
                "defect_image",
                "defectImage",
                "classifier_image",
                "classifierImage",
                "clip_image",
                "clipImage",
                "thumbnail",
        ):
            if key in value:
                yield value[key]
        for child in value.values():
            if isinstance(child, (dict, list, tuple)):
                yield from _iter_defect_data_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_defect_data_values(child)
    elif isinstance(value, str):
        yield value


def _defect_data_image_paths(defect: CoilDefect) -> list[Path]:
    defect_data = getattr(defect, "defectData", None)
    if not defect_data:
        return []

    parsed_values = [defect_data]
    if isinstance(defect_data, str):
        try:
            parsed_values.append(json.loads(defect_data))
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    image_paths = []
    seen_paths = set()
    image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    for parsed_value in parsed_values:
        for value in _iter_defect_data_values(parsed_value):
            if not isinstance(value, str):
                continue
            path_text = value.strip().strip('"').strip("'")
            if not path_text or path_text.startswith(("http://", "https://")):
                continue
            image_path = Path(path_text)
            if image_path.suffix.lower() not in image_suffixes:
                continue
            if not image_path.is_absolute():
                for config in serverConfigProperty.surfaceConfigPropertyDict.values():
                    candidate = Path(config.saveFolder) / image_path
                    if candidate not in seen_paths:
                        seen_paths.add(candidate)
                        image_paths.append(candidate)
                continue
            if image_path not in seen_paths:
                seen_paths.add(image_path)
                image_paths.append(image_path)
    return image_paths


def _classifier_dirs(defect: CoilDefect,
                     defect_name: str | None = None) -> list[Path]:
    coil_id = getattr(defect, "secondaryCoilId", "")
    surface = getattr(defect, "surface", None)
    configs = []
    surface_config = serverConfigProperty.surfaceConfigPropertyDict.get(surface)
    if surface_config:
        configs.append(surface_config)
    configs.extend(serverConfigProperty.surfaceConfigPropertyDict.values())

    candidate_dirs = []
    seen_dirs = set()
    for config in configs:
        save_folder = Path(config.saveFolder)
        for name in _defect_name_candidates(defect, defect_name):
            for classifier_dir in (
                    save_folder / str(coil_id) / "classifier" / name,
                    save_folder.parent / "classifier_save" / "classifier" /
                    name,
            ):
                if classifier_dir in seen_dirs:
                    continue
                seen_dirs.add(classifier_dir)
                candidate_dirs.append(classifier_dir)
    return candidate_dirs


def get_pil_image_from_classifier_save(defect: CoilDefect,
                                       defect_name: str | None = None,
                                       crop_margin: int | None = None):
    """Load a saved classifier crop for a defect if it exists."""
    try:
        if crop_margin is None:
            for image_path in _defect_data_image_paths(defect):
                image = _load_image_copy(image_path)
                if image is not None:
                    return image

        x1, y1, *_ = _defect_box_values(defect)
        coil_id = getattr(defect, "secondaryCoilId", "")
        glob_patterns = [
            f"{coil_id}_{x1}_{y1}_*.png",
            f"{coil_id}_{x1}_{y1}_*.jpg",
            f"{coil_id}_{x1}_{y1}_*.jpeg",
        ]
        for classifier_dir in _classifier_dirs(defect, defect_name):
            if not classifier_dir.exists():
                continue
            for name in _classifier_file_names(defect, crop_margin):
                image_path = classifier_dir / name
                image = _load_image_copy(image_path)
                if image is not None:
                    return image
            if crop_margin is not None:
                continue
            for glob_pattern in glob_patterns:
                for image_path in sorted(classifier_dir.glob(glob_pattern)):
                    image = _load_image_copy(image_path)
                    if image is not None:
                        return image

        return None

    except Exception as e:
        print(f"Error loading from classifier: {e}")
        return None


def _crop_source_for_defect(defect: CoilDefect) -> tuple[str, str]:
    if _is_2d_defect(defect):
        return "source", "AREA"
    return "image", "GRAY"


def _get_cached_source_image(defect: CoilDefect,
                             source_image_cache: dict | None = None):
    if source_image_cache is None:
        source_image_cache = {}

    source_type, image_type = _crop_source_for_defect(defect)
    key = (str(getattr(defect, "secondaryCoilId", "")),
           str(getattr(defect, "surface", "")), source_type, image_type)
    if key in source_image_cache:
        return source_image_cache[key]

    image = get_pil_image(defect.surface,
                          defect.secondaryCoilId,
                          source_type=source_type,
                          type_=image_type)
    if image is None:
        return None
    source_image_cache[key] = image.copy()
    return source_image_cache[key]


def _crop_defect_image_cached(defect: CoilDefect,
                              source_image_cache: dict | None = None):
    source_image = _get_cached_source_image(defect, source_image_cache)
    if source_image is None:
        return None

    x, y, w, h, *_ = _defect_box_values(defect)
    box = [x, y, max(w, 1), max(h, 1)]
    crop_margin = _crop_margin_for_defect(defect)
    if crop_margin is None:
        crop_box = expansion_box(box, source_image.size, 0.1, 10, 50)
    else:
        crop_box = _expand_box_with_margin(box, source_image.size,
                                           crop_margin)
    return source_image.crop([
        crop_box[0],
        crop_box[1],
        crop_box[2] + crop_box[0],
        crop_box[3] + crop_box[1],
    ])


def _expand_box_with_margin(box, image_size, margin: int):
    x, y, w, h = box
    width, height = image_size
    x1 = max(0, int(x) - margin)
    y1 = max(0, int(y) - margin)
    x2 = min(width, int(x) + int(w) + margin)
    y2 = min(height, int(y) + int(h) + margin)
    if x2 <= x1:
        x2 = min(width, x1 + 1)
    if y2 <= y1:
        y2 = min(height, y1 + 1)
    return x1, y1, x2 - x1, y2 - y1


def _classifier_save_path(defect: CoilDefect,
                          defect_name: str | None = None,
                          crop_margin: int | None = None) -> Path | None:
    dirs = _classifier_dirs(defect, defect_name)
    if not dirs:
        return None
    return dirs[0] / _classifier_file_names(defect, crop_margin)[0]


def _save_classifier_crop(defect: CoilDefect,
                          image: Image.Image,
                          defect_name: str | None = None,
                          crop_margin: int | None = None) -> None:
    image_path = _classifier_save_path(defect, defect_name, crop_margin)
    if image_path is None:
        return

    try:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(image_path, format="PNG")
    except Exception as e:
        print(
            f"[Export] failed to save defect crop coil={defect.secondaryCoilId}, "
            f"surface={defect.surface}, defect={defect_name or defect.defectName}: {e}"
        )


def _close_source_image_cache(source_image_cache: dict) -> None:
    for image in source_image_cache.values():
        try:
            image.close()
        except Exception as e:
            pass
    source_image_cache.clear()


def get_pil_image_for_export(defect: CoilDefect,
                             source_image_cache: dict | None = None,
                             defect_name: str | None = None):
    """Prefer persisted defect crops; crop the source image only as fallback."""
    crop_margin = _crop_margin_for_defect(defect)
    image = get_pil_image_from_classifier_save(defect, defect_name,
                                               crop_margin)
    if image is not None:
        return image

    try:
        image = _crop_defect_image_cached(defect, source_image_cache)
        if image is not None:
            _save_classifier_crop(defect, image, defect_name, crop_margin)
            return image
        if crop_margin is not None:
            return get_pil_image_from_classifier_save(defect, defect_name)
        return None
    except Exception as e:
        print(
            f"[Export] failed to crop defect image from source coil={defect.secondaryCoilId}, "
            f"surface={defect.surface}, defect={defect.defectName}: {e}"
        )
        if crop_margin is not None:
            return get_pil_image_from_classifier_save(defect, defect_name)
        return None


def get_item_data(secondary_coil: SecondaryCoil,
                  export_config: ExportConfig = None):
    res_data = {}
    alarm_info_dict = {"S": None, "L": None}
    defects = get_defects(secondary_coil)
    print(
        f"[Export] get_item_data: coil_id={secondary_coil.Id}, defects count={len(defects) if defects else 0}"
    )

    if export_config.export_header_data:
        res_data.update(get_header_data(secondary_coil))  # 添加 二级数据信息
    # if len(defects) <= 0:
    #     return res_data
    res_data.update({"defects": defects})
    # alarm_info_list = secondary_coil.childrenAlarmInfo
    # for alarm_info in alarm_info_list:
    #     alarm_info_dict[alarm_info.surface]=alarm_info
    return res_data


def export_defect_image_by_names(coil_id_list,
                                 worksheet,
                                 export_config: ExportConfig = None,
                                 names=None,
                                 in_list=True,
                                 format_=None,
                                 defect_filter=None):
    print(
        f"[Export] export_defect_image_by_names called, names={names}, in_list={in_list}"
    )
    if names is None:
        names = []
    data_all = []
    head_key_list = []
    source_image_cache = {}
    skipped_images = []  # 记录跳过的图像
    defect_count_total = 0  # 统计总缺陷数
    image_found_count = 0  # 统计找到的图像数
    print(f"[Export] coil_id_list: {len(coil_id_list)}")
    for secondaryCoil in coil_id_list:
        item_dict = get_item_data(secondaryCoil, export_config)
        if item_dict is None:
            continue

        data_all.append(item_dict)
        if len(item_dict.keys()) > len(head_key_list):
            head_key_list = list(item_dict.keys())

    data = [head_key_list]
    for itemData in data_all:
        row = []
        for key in head_key_list:
            try:
                row.append(itemData[key])
            except (Exception, ) as e:
                row.append("")
        data.append(row)

    for row_num, row_data in enumerate(data):
        if row_num == 0:
            worksheet.write_row(row_num, 0, row_data)
            continue

        defects = row_data[-1]
        text_row = row_data[:-1]
        for index, data_item in enumerate(text_row):
            worksheet.write(row_num, index, data_item)
        offset = len(row_data)
        for index, defect in enumerate(defects):
            if defect_filter is not None and not defect_filter(defect):
                continue

            defect_name = CONFIG.defectClassesProperty.format_name(
                defect.defectName)
            if in_list:
                if defect_name not in names:
                    continue
            else:
                if defect_name in names:
                    continue

            defect_count_total += 1  # 统计导出的缺陷数
            image = get_pil_image_for_export(defect, source_image_cache,
                                             defect_name)
            # 失败跳过逻辑：如果图像加载失败，跳过该缺陷
            if image is None:
                skipped_images.append({
                    'coil_id': defect.secondaryCoilId,
                    'defect_name': defect_name,
                    'x': defect.defectX,
                    'y': defect.defectY
                })
                continue

            image_found_count += 1  # 统计找到的图像数
            defect: CoilDefect
            text = f"{defect_name}\n宽：{int((defect.defectW*0.34))}\n高：{int(defect.defectH*0.34)}"
            insert_image_and_name(worksheet, row_num, offset, text, image,
                                  format_)
            try:
                image.close()
            except Exception as e:
                pass
            offset += 2

    # 输出统计信息
    print(
        f"[Export] Total defects: {defect_count_total}, "
        f"Images found: {image_found_count}, Skipped: {len(skipped_images)}"
    )
    print(f"[Export] Source images loaded for crop: {len(source_image_cache)}")
    _close_source_image_cache(source_image_cache)

    # 输出跳过的图像统计
    if skipped_images:
        print(
            f"Warning: Skipped {len(skipped_images)} defect images due to loading errors"
        )
        for item in skipped_images[:5]:  # 只打印前5个
            print(
                f"  - Coil {item['coil_id']}: {item['defect_name']} at ({item['x']}, {item['y']})"
            )
        if len(skipped_images) > 5:
            print(f"  ... and {len(skipped_images) - 5} more")


def _is_2d_defect(defect: CoilDefect) -> bool:
    defect_name = str(getattr(defect, "defectName", "") or "")
    return defect_name.upper().startswith("2D")


def _is_3d_defect(defect: CoilDefect) -> bool:
    return not _is_2d_defect(defect)


def _is_show_defect_class(defect: CoilDefect) -> bool:
    raw_name = str(getattr(defect, "defectName", "") or "")
    try:
        defect_name = CONFIG.defectClassesProperty.format_name(raw_name)
    except Exception:
        defect_name = raw_name

    defect_config = CONFIG.defectClassesProperty.data.get(defect_name)
    if defect_config is None:
        defect_config = CONFIG.defectClassesProperty.data.get(raw_name)
    if defect_config is None:
        return bool(CONFIG.defectClassesProperty.default.get("show", True))
    return bool(defect_config.get("show", True))


def _is_3d_show_defect(defect: CoilDefect) -> bool:
    return _is_3d_defect(defect) and _is_show_defect_class(defect)


def _is_3d_un_show_defect(defect: CoilDefect) -> bool:
    return _is_3d_defect(defect) and not _is_show_defect_class(defect)


def _sheet_name(base_name: str, suffix: str) -> str:
    base_name = str(base_name or "Sheet")
    suffix = str(suffix or "")[:31]
    invalid_chars = set("[]:*?/\\")
    safe_base_name = "".join("_" if char in invalid_chars else char
                             for char in base_name)
    return f"{safe_base_name[:max(0, 31 - len(suffix))]}{suffix}"


def _get_defect_number(defect: CoilDefect, field: str, default=0):
    value = getattr(defect, field, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_area_image(coil_id, surface: str):
    try:
        image = DataGet("source", surface, str(coil_id), "AREA",
                        False).get_image(pil=True)
        if image is None:
            return None
        return image.convert("RGB")
    except Exception as e:
        print(
            f"[Export] failed to load AREA image coil={coil_id}, surface={surface}: {e}"
        )
        return None


def _defect_label(defect: CoilDefect) -> str:
    defect_name = str(getattr(defect, "defectName", "") or "2D")
    try:
        defect_name = CONFIG.defectClassesProperty.format_name(defect_name)
    except Exception:
        pass
    confidence = _get_defect_number(defect, "defectSource", None)
    if confidence is not None and 0 <= confidence <= 1:
        return f"{defect_name} {confidence * 100:.1f}%"
    return defect_name


def _draw_area_defects(area_image: Image.Image,
                       defects: list[CoilDefect],
                       max_side: int = 720) -> Image.Image:
    width, height = area_image.size
    scale = min(1.0, max_side / max(width, height))
    if scale < 1.0:
        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS",
                             Image.BICUBIC)
        draw_image = area_image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            resampling)
    else:
        draw_image = area_image.copy()

    draw = ImageDraw.Draw(draw_image)
    font = ImageFont.load_default()
    line_width = max(2, int(3 * max(scale, 1)))

    for index, defect in enumerate(defects, start=1):
        x = _get_defect_number(defect, "defectX")
        y = _get_defect_number(defect, "defectY")
        w = max(_get_defect_number(defect, "defectW", 1), 1)
        h = max(_get_defect_number(defect, "defectH", 1), 1)

        sx = x * scale
        sy = y * scale
        sw = max(w * scale, 2)
        sh = max(h * scale, 2)
        cx = sx + sw / 2
        cy = sy + sh / 2

        marker_size = max(14, int(max(sw, sh, 14)))
        marker_left = max(0, cx - marker_size / 2)
        marker_top = max(0, cy - marker_size / 2)
        marker_right = min(draw_image.size[0] - 1, cx + marker_size / 2)
        marker_bottom = min(draw_image.size[1] - 1, cy + marker_size / 2)

        color = "#ff3b30" if getattr(defect, "surface",
                                     "S") == "S" else "#00d5ff"
        draw.rectangle([sx, sy, sx + sw, sy + sh],
                       outline=color,
                       width=line_width)
        draw.rectangle([marker_left, marker_top, marker_right, marker_bottom],
                       outline=color,
                       width=line_width)
        draw.line([cx - marker_size / 2, cy, cx + marker_size / 2, cy],
                  fill=color,
                  width=line_width)
        draw.line([cx, cy - marker_size / 2, cx, cy + marker_size / 2],
                  fill=color,
                  width=line_width)

        label = f"{index}. {_defect_label(defect)}"
        text_x = min(max(0, marker_right + 4), max(0,
                                                   draw_image.size[0] - 120))
        text_y = max(0, marker_top - 2)
        text_bbox = draw.textbbox((text_x, text_y), label, font=font)
        draw.rectangle(text_bbox, fill="#000000")
        draw.text((text_x, text_y), label, fill=color, font=font)

    return draw_image


def _insert_area_defect_image(worksheet, row_num: int, image_col: int,
                              image: Image.Image):
    image_stream = io.BytesIO()
    image.save(image_stream, format="PNG")
    image_stream.seek(0)
    worksheet.insert_image(
        row_num, image_col, "area_defects.png", {
            "image_data": image_stream,
            "x_scale": 1,
            "y_scale": 1,
            "object_position": 1,
        })


def _format_area_defect_details(defects: list[CoilDefect]) -> str:
    details = []
    for index, defect in enumerate(defects, start=1):
        x = int(_get_defect_number(defect, "defectX"))
        y = int(_get_defect_number(defect, "defectY"))
        w = int(_get_defect_number(defect, "defectW"))
        h = int(_get_defect_number(defect, "defectH"))
        details.append(f"{index}. {_defect_label(defect)} ({x},{y},{w},{h})")
    return "\n".join(details)


def _area_sheet_name(base_name: str) -> str:
    return _sheet_name(base_name, "_2D")


def _defect_3d_sheet_name(base_name: str) -> str:
    return _sheet_name(base_name, "_3D")


def _defect_3d_un_show_sheet_name(base_name: str) -> str:
    return _sheet_name(_defect_3d_sheet_name(base_name), "_屏蔽")


def export_3d_defect_image(coil_id_list,
                           workbook,
                           export_config: ExportConfig = None,
                           format_=None):
    print(
        f"[Export] export_3d_defect_image called with {len(coil_id_list)} coils"
    )
    print(
        f"[Export] show_name_list: {CONFIG.defectClassesProperty.show_name_list}"
    )

    if not export_config.defect_show_info and not export_config.defect_un_show_info:
        return

    if export_config.defect_show_info:
        worksheet = workbook.add_worksheet(
            _defect_3d_sheet_name(export_config.worksheet_defect_image_name))
        export_defect_image_by_names(coil_id_list,
                                     worksheet,
                                     export_config,
                                     [],
                                     False,
                                     format_=format_,
                                     defect_filter=_is_3d_show_defect)

    if export_config.defect_un_show_info:
        worksheet = workbook.add_worksheet(
            _defect_3d_un_show_sheet_name(
                export_config.worksheet_defect_image_name))
        export_defect_image_by_names(coil_id_list,
                                     worksheet,
                                     export_config,
                                     [],
                                     False,
                                     format_=format_,
                                     defect_filter=_is_3d_un_show_defect)


def export_area_2d_defect_image(coil_id_list,
                                workbook,
                                export_config: ExportConfig = None,
                                format_=None):
    worksheet = workbook.add_worksheet(
        _area_sheet_name(export_config.worksheet_defect_image_name))
    export_defect_image_by_names(coil_id_list,
                                 worksheet,
                                 export_config,
                                 [],
                                 False,
                                 format_=format_,
                                 defect_filter=_is_2d_defect)
    return



def export_defect_show_image(coil_id_list,
                             workbook,
                             export_config: ExportConfig = None,
                             format_=None):
    print(
        f"[Export] export_defect_show_image called with {len(coil_id_list)} coils"
    )
    print(
        f"[Export] show_name_list: {CONFIG.defectClassesProperty.show_name_list}"
    )

    worksheet = workbook.add_worksheet(
        _sheet_name(export_config.worksheet_defect_image_name, "_显示"))
    export_defect_image_by_names(coil_id_list,
                                 worksheet,
                                 export_config,
                                 CONFIG.defectClassesProperty.show_name_list,
                                 format_=format_,
                                 defect_filter=_is_3d_defect)


def export_defect_un_show_image(coil_id_list,
                                workbook,
                                export_config: ExportConfig = None,
                                format_=None):
    worksheet = workbook.add_worksheet(
        _sheet_name(export_config.worksheet_defect_image_name, "_屏蔽"))
    export_defect_image_by_names(coil_id_list,
                                 worksheet,
                                 export_config,
                                 CONFIG.defectClassesProperty.show_name_list,
                                 False,
                                 format_=format_,
                                 defect_filter=_is_3d_defect)


def insert_image_and_name(worksheet, row_num, index, text, image,
                          format_: XlsxWriterFormatConfig):
    worksheet.set_row(row_num, 150)  # 设置第一行的高度
    worksheet.set_column(index + 1, index + 1, 25)  # 设置A列的宽度
    # 设置单元格格式，使其支持自动换行
    worksheet.write(row_num, index, text, format_.cell_format)

    new_size = 150
    # Get the original width and height
    width, height = image.size
    if width > new_size or height > new_size:
        # Calculate the scaling factor
        scaling_factor = min(new_size / width, new_size / height)
        # Calculate the new dimensions
        new_width = int(width * scaling_factor)
        new_height = int(height * scaling_factor)
        # Resize the image
        image = image.resize((new_width, new_height))

    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_stream.seek(0)  # 将指针移到开头
    worksheet.insert_image(row_num, index + 1, 'image.png', {
        'image_data': image_stream,
        'x_scale': 1,
        'y_scale': 1
    })
    # 添加表格格式
    # worksheet.add_table(
    #     0, 0, len(data) - 1, len(data[0]) - 1,  # 表格的范围
    #     {
    #         "columns": [{"header": col} for col in data[0]],  # 设置表头
    #         "style": "Table Style Medium 9",  # 表格样式
    #         "autofilter": True,  # 启用自动筛选
    #     }
    # )
