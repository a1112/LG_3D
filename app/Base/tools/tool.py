import os

import cv2
import numpy as np
from PIL import Image

from Base.property.Types import Point2D
from Base.utils.DetectionSpeedRecord import DetectionSpeedRecord
from Base.utils.Log import logger


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, value, default)
        return default


def showImage(image, name="image", *, enabled=None, wait_ms=None):
    if enabled is None:
        enabled = _env_bool("LG3D_DEBUG_IMAGE_SHOW", False)
    if not enabled:
        logger.debug("skip debug image window: %s", name)
        return False

    if isinstance(image, Image.Image):
        image = np.array(image)
    if wait_ms is None:
        wait_ms = max(_env_int("LG3D_DEBUG_IMAGE_WAIT_MS", 1), 1)
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(name, 800, 800)
    cv2.imshow(name, image)
    cv2.waitKey(wait_ms)
    return True


def getMask(gray_image):
    if isinstance(gray_image, Image.Image):
        gray_image = np.array(gray_image)

    blurred_image = cv2.GaussianBlur(gray_image, (9, 9), 0)

    # 应用阈值处理
    ret, binary_image = cv2.threshold(blurred_image, 30, 255, cv2.THRESH_BINARY)
    return binary_image


def get_foreground(gray_image, direction="L", key=None):
    if isinstance(gray_image, Image.Image):
        gray_image = np.array(gray_image)
    source_image = np.asarray(gray_image)
    if source_image.ndim == 3:
        gray_for_mask = cv2.cvtColor(source_image[..., :3], cv2.COLOR_RGB2GRAY)
    else:
        gray_for_mask = source_image
    if gray_for_mask.dtype != np.uint8:
        gray_for_mask = np.clip(np.nan_to_num(gray_for_mask, nan=0), 0, 255).astype(np.uint8)
    key_text = str(key or "")
    blurred_image = cv2.GaussianBlur(gray_for_mask, (9, 9), 0)
    # 应用阈值处理
    _, binary_image = cv2.threshold(blurred_image, 65, 210, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # ret, binary_image = cv2.threshold(blurred_image, 70, 255, cv2.THRESH_BINARY)
    # 应用形态学操作去除噪声
    kernel = np.ones((5, 5), np.uint8)  # 调整核的大小
    cleaned_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel, iterations=4)
    # cleaned_image=binary_image
    # 找到轮廓
    contours, _ = cv2.findContours(cleaned_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = list(contours)
    contours.sort(key=cv2.contourArea, reverse=True)
    logger.debug("foreground contour areas: %s", [cv2.contourArea(c) for c in contours])
    # 创建掩膜并填充最大的轮廓
    mask = np.zeros_like(gray_for_mask)
    new_contours = []
    for c in contours:
        if direction == "L" or "D" in key_text or "M" in key_text:
            if cv2.boundingRect(c)[0] < 300:
                new_contours.append(c)
        elif direction == "R":

            if cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2] > cleaned_image.shape[1] - 500:
                new_contours.append(c)
    if contours and not new_contours:
        new_contours = [contours[0]]
        logger.warning("foreground contour fallback: direction=%s key=%s", direction, key_text)
    if new_contours:
        largest_contour = max(new_contours, key=cv2.contourArea)
        rec2 = cv2.boundingRect(largest_contour)
        cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    # 应用掩膜移除背景
    # foreground = cv2.bitwise_and(gray_image, gray_image, mask=mask)
    # return foreground, mask,rec
    return source_image, mask


def auto_crop(key, image, star_pos, direction):
    gray_image, mask = get_foreground(image, direction, key)

    rec = crop_max_image_black_edges(key, mask, star_pos)
    x, y, w, h = rec
    return gray_image[y:y + h, x:x + w], mask[y:y + h, x:x + w], rec


def crop_max_image_black_edges(key, image, star_pos):
    # 图像列求和，检测哪些列是主要黑色的
    # column_sum = np.sum(gray, axis=0)
    key_text = str(key or "")
    image = np.asarray(image)
    if image.ndim < 2 or image.shape[0] == 0 or image.shape[1] == 0:
        logger.warning("crop_max_image_black_edges skip empty image: key=%s shape=%s", key_text, getattr(image, "shape", None))
        return [0, 0, 0, 0]
    if image.ndim == 3:
        foreground = np.any(np.nan_to_num(image, nan=0) > 100, axis=2)
    else:
        foreground = np.nan_to_num(image, nan=0) > 100
    h, w = foreground.shape
    if not np.any(foreground):
        logger.warning("crop_max_image_black_edges found no foreground: key=%s shape=%s", key_text, foreground.shape)
        return [0, 0, w, h]
    try:
        crop_left = int(star_pos[0])
        crop_right = int(star_pos[1])
    except (TypeError, ValueError, IndexError):
        logger.warning("invalid crop star_pos=%s for key=%s, use full bounds", star_pos, key_text)
        crop_left = 0
        crop_right = 0
    column_no_black_count = np.sum(foreground, axis=0)
    left_index = min(max(crop_left, 0), w - 1)
    right_index = min(max(w - max(crop_right, 0), 0), w - 1)
    max_l = left_index + 300  # 规定最大裁剪
    min_r = right_index - 800  # 规定最大裁剪
    # 从左侧找到第一个非黑色列
    max_l = min(max_l, w - 1)
    min_r = max(min_r, 0)
    # l_threshold = 0.05 if "D" in key else 0.25
    # r_threshold = 0.25
    # while left_index > max_l or column_no_black_count[left_index]>5000*255: # /(column_no_black_count[max_l+100]) < l_threshold:
    #     left_index += 1
    l_limit_base = 10 if "S_D" in key_text else 500
    l_limit = min(l_limit_base, max(1, h // 2))
    while True:
        if left_index > max_l:
            break
        if column_no_black_count[left_index] > l_limit:
            break
        left_index += 1

    # 从右侧找到第一个非黑色列
    # while right_index < maxR and column_no_black_count[right_index]>5*255: #/(column_no_black_count[maxR-100]) < r_threshold:
    #     right_index -= 1
    r_limit_base = 10 if "L_D" in key_text else 500
    r_limit = min(r_limit_base, max(1, h // 2))
    while True:
        if right_index < min_r:
            break
        if column_no_black_count[right_index] > r_limit:
            break
        right_index -= 1
    logger.debug("r_index %s %s %s %s", key_text, right_index, w - right_index, column_no_black_count[right_index])
    # showImage(image)
    # 保存裁剪后的图像
    left_padding = 0 if "S_D" in key_text else 20
    right_padding = 0 if "L_D" in key_text else 20
    x = left_index + left_padding
    right_edge = right_index + 1 - right_padding
    if right_edge <= x:
        x = left_index
        right_edge = right_index + 1
    x = min(max(x, 0), w - 1)
    right_edge = min(max(right_edge, x + 1), w)
    width = right_edge - x
    if width <= 0:
        logger.warning(
            "invalid crop range key=%s x=%s right=%s shape=%s, use full image",
            key_text,
            x,
            right_edge,
            foreground.shape,
        )
        return [0, 0, w, h]
    # tools.tool.showImage(image[:, x:x + width],f"{key}_{[x, 0, w-(width+x), h]}")
    return [x, 0, width, h]


def cropImage(image, cropLeft, cropRight):
    width, height = image.size
    left = cropLeft
    right = width - cropRight
    top = 0
    bottom = height
    image = image.crop((left, top, right, bottom))
    return image


def horizontal_projection_first_nonzero(mask):
    if isinstance(mask, Image.Image):
        mask = np.array(mask)
    mask = np.asarray(mask)
    if mask.ndim < 2 or mask.shape[0] == 0 or mask.shape[1] == 0:
        logger.warning("horizontal_projection_first_nonzero skip empty mask: shape=%s", getattr(mask, "shape", None))
        return np.array([], dtype=np.int32)
    height = mask.shape[0]
    # 使用np.argmax找到第一个非零值的索引
    foreground = mask > 150
    non_zero_indices = np.argmax(foreground, axis=0)
    # 处理整列都是零的情况
    non_zero_indices[np.all(~foreground, axis=0)] = height
    return non_zero_indices


def find_nearest(array, value):
    # 查找最接近的值的索引
    idx = np.searchsorted(array, value, side="left")
    if idx > 0 and (idx == len(array) or abs(value - array[idx - 1]) <= abs(value - array[idx])):
        return array[idx - 1], idx - 1
    else:
        return array[idx], idx


def getDiff(abs_diff, num=0):
    whereArray = np.where(abs_diff == num)
    if len(whereArray[0]) > 0:
        return list(whereArray[0])
    else:
        if num > 5:
            return []
        return getDiff(abs_diff, num + 1)


def find_cross_points(projections):
    cross_points = []
    for i in range(1, len(projections)):
        l_ = projections[i - 1]
        r_ = projections[i]
        l_len = len(l_)
        if l_len == 0 or len(r_) == 0:
            logger.warning("find_cross_points skip empty projection: left=%s, right=%s", l_len, len(r_))
            cross_points.append((0, 0))
            continue
        abs_diff_l_r = np.abs(l_ - r_[0])
        f_l_List = getDiff(abs_diff_l_r, 0)
        if f_l_List:
            f_l_index = f_l_List[-1]
        else:
            f_l_index = l_len
        abs_diff_r_l = np.abs(r_ - l_[-1])
        f_r_list = getDiff(abs_diff_r_l, 0)
        if f_r_list:
            f_r_index = f_r_list[0]
        else:
            f_r_index = 0
        cross_points.append((int(l_len - f_l_index), int(f_r_index)))
    return cross_points


def crop_black_border(gray):
    if isinstance(gray, Image.Image):
        gray = np.array(gray)
    gray = np.asarray(gray)
    if gray.ndim < 2 or gray.shape[0] == 0 or gray.shape[1] == 0:
        logger.warning("crop_black_border skip empty image: shape=%s", getattr(gray, "shape", None))
        return 0, 0, 0, 0
    if gray.ndim == 3:
        foreground = np.any(np.nan_to_num(gray, nan=0) > 0, axis=2)
    else:
        foreground = np.nan_to_num(gray, nan=0) > 0
    binary = foreground.astype(np.uint8)
    # 寻找非黑色区域的边界
    coords = cv2.findNonZero(binary)
    if coords is None:
        logger.warning("crop_black_border found no foreground, using full image: shape=%s", gray.shape)
        return 0, 0, gray.shape[1], gray.shape[0]
    # 计算边界框
    x, y, w, h = cv2.boundingRect(coords)
    # 裁剪图像
    return x, y, w, h


def rotate_around_x_axis(height_data, angle):
    """
    旋转二维高度数据围绕X轴旋转，保持原来的宽高

    参数:
    height_data (numpy.ndarray): 二维高度数据
    angle (float): 旋转角度（以度为单位）

    返回:
    numpy.ndarray: 旋转后的高度数据
    """
    rows, cols = height_data.shape
    x = np.arange(cols)
    y = np.arange(rows)
    xx, yy = np.meshgrid(x, y)

    # 构建绕X轴的旋转矩阵
    angle_rad = np.radians(angle)
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(angle_rad), -np.sin(angle_rad)],
                   [0, np.sin(angle_rad), np.cos(angle_rad)]])

    # 应用旋转矩阵
    points = np.vstack((xx.ravel(), yy.ravel(), height_data.ravel())).T
    rotated_points = np.dot(points, Rx.T)

    # 将旋转后的点转换回二维高度数据
    rotated_height_data = rotated_points[:, 2].reshape(height_data.shape)

    return rotated_height_data

@DetectionSpeedRecord.timing_decorator("get_horizontal_projection_list")
def get_horizontal_projection_list(image_list):
    horizontal_projection_list = []
    for index, image in enumerate(image_list):  # 进行投影
        horizontal_projection = horizontal_projection_first_nonzero(image)
        horizontal_projection_list.append(horizontal_projection)
    return horizontal_projection_list


def hstack_3d(npy_list, window_size=100, max_blocks=3, join_mask_image=None):
    """
    水平拼接多个 3D 高度矩阵，并对相邻块的边缘做高度对齐。

    Args:
        npy_list (List[np.ndarray]): 需要拼接的 3D 高度矩阵列表，按顺序排列。
        window_size (int): 用于边缘检测的窗口高度（连续 window_size 行非零判定为有效区域）。
        max_blocks (int): 在边缘上最多检测多少个有效窗口，用最后一个窗口的行号来对齐。
        join_mask_image (np.ndarray | None): 未使用，保留接口。

    Returns:
        np.ndarray: 拼接后的 3D 高度矩阵。
    """

    def find_valid_rows(column_data, ws, max_n, min_value=0):
        """
        在单列数据中查找连续 ws 行都大于 min_value 的起始行索引，最多返回 max_n 个。
        """
        idxs = []
        total = len(column_data)
        for i in range(total // ws):
            start = i * ws
            end = start + ws
            if np.all(column_data[start:end] > min_value):
                idxs.append(start)
                if len(idxs) >= max_n:
                    break
        return idxs

    def edge_mean(data, start_row, width=3, side="left"):
        """
        计算指定行附近、左/右边缘若干列的均值，用于对齐。
        """
        if side == "left":
            cols = data[start_row:start_row + window_size, :width]
        else:
            cols = data[start_row:start_row + window_size, -width:]
        valid = cols[cols > 1500]
        return np.mean(valid) if valid.size else np.nan

    def apply_valid_delta(data, delta):
        if not np.isfinite(delta):
            return data
        valid = data > 0
        if not np.any(valid):
            return data

        aligned = data.astype(np.float32, copy=True)
        aligned[valid] = aligned[valid] + delta
        aligned[~valid] = 0

        if np.issubdtype(data.dtype, np.integer):
            dtype_info = np.iinfo(data.dtype)
            aligned = np.clip(np.rint(aligned), dtype_info.min,
                              dtype_info.max)
            return aligned.astype(data.dtype)
        return aligned.astype(data.dtype, copy=False)

    stitched = [npy_list[0]]
    for idx in range(1, len(npy_list)):
        left = stitched[-1]
        right = npy_list[idx]

        # 取右块左边缘和左块右边缘
        r_left_col = right[:, 0]
        l_right_col = left[:, -1]

        # 找到右块左边缘的有效行窗口
        valid_rows = find_valid_rows(r_left_col, window_size, max_blocks, min_value=0)
        if not valid_rows:
            stitched.append(right)
            continue

        sample_row = valid_rows[-1]
        mean_l = edge_mean(left, sample_row, side="right")
        mean_r = edge_mean(right, sample_row, side="left")

        # 对齐：如果均值有效且差值合理，平移右块
        if np.isnan(mean_l) or np.isnan(mean_r) or abs(mean_l - mean_r) > 1e6:
            logger.error("hstack_3d align skip: mean_l=%s, mean_r=%s, row=%s", mean_l, mean_r, sample_row)
        else:
            right = apply_valid_delta(right, mean_l - mean_r)

        stitched.append(right)

    return np.hstack(stitched)


def _is_plausible_inner_ellipse(inner_ellipse, outer_ellipse):
    if inner_ellipse is None or outer_ellipse is None:
        return False
    (inner_x, inner_y), inner_axes, _ = inner_ellipse
    (outer_x, outer_y), outer_axes, _ = outer_ellipse
    inner_min, inner_max = sorted(inner_axes)
    outer_min, outer_max = sorted(outer_axes)
    if inner_min <= 0 or outer_min <= 0:
        return False
    return (
        np.hypot(inner_x - outer_x, inner_y - outer_y) <= outer_min * 0.12
        and inner_min >= outer_min * 0.12
        and inner_max <= outer_max * 0.72
        and inner_max / inner_min <= 1.35
    )


def _inner_ellipse_from_radial_edges(binary, outer_ellipse):
    (center_x, center_y), outer_axes, _ = outer_ellipse
    outer_radius = min(outer_axes) / 2.0
    min_radius = int(outer_radius * 0.12)
    max_radius = int(outer_radius * 0.72)
    height, width = binary.shape
    points = []
    distances = []

    for angle in np.linspace(0, 2 * np.pi, 360, endpoint=False):
        radii = np.arange(min_radius, max_radius + 1)
        xs = np.rint(center_x + radii * np.cos(angle)).astype(np.int32)
        ys = np.rint(center_y + radii * np.sin(angle)).astype(np.int32)
        inside = (xs >= 0) & (xs < width) & (ys >= 0) & (ys < height)
        xs, ys, radii = xs[inside], ys[inside], radii[inside]
        if radii.size < 3:
            continue
        foreground = binary[ys, xs] > 0
        stable = np.convolve(foreground.astype(np.uint8),
                             np.ones(3, dtype=np.uint8),
                             mode="valid") == 3
        transitions = np.flatnonzero(stable)
        if transitions.size == 0:
            continue
        index = int(transitions[0])
        points.append((float(xs[index]), float(ys[index])))
        distances.append(int(radii[index]))

    if len(points) < 120:
        return None
    distances = np.asarray(distances, dtype=np.float32)
    median_distance = float(np.median(distances))
    keep = ((distances >= median_distance * 0.7)
            & (distances <= median_distance * 1.3))
    points = np.asarray(points, dtype=np.float32)[keep]
    if len(points) < 100:
        return None
    contour = np.rint(points).astype(np.int32).reshape(-1, 1, 2)
    ellipse = cv2.fitEllipse(contour)
    ellipse_axes = sorted(ellipse[1])
    if ellipse_axes[1] / ellipse_axes[0] > 1.05:
        # With one camera sector missing, fitEllipse stretches toward the
        # absent arc. The radial median is stable because it only uses intact
        # directions, and a coil eye is nominally circular.
        diameter = median_distance * 2.0
        ellipse = (ellipse[0], (diameter, diameter), 0.0)
    return ellipse if _is_plausible_inner_ellipse(ellipse,
                                                   outer_ellipse) else None


def get_inner_ellipse_by_mask(mask):
    """Return a stable coil-eye ellipse even when a missing frame opens it."""
    source = np.asarray(mask)
    if source.ndim == 3:
        source = np.max(source, axis=2)
    if source.ndim != 2 or source.size == 0:
        return None
    binary = np.where(source > 150, 255, 0).astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    outer_contour = max(contours, key=cv2.contourArea)
    if len(outer_contour) < 5:
        return None
    outer_ellipse = cv2.fitEllipse(outer_contour)
    outer_mask = np.zeros(binary.shape, dtype=np.uint8)
    cv2.ellipse(outer_mask, outer_ellipse, 255, thickness=cv2.FILLED)
    hole_candidates = np.where((outer_mask > 0) & (binary == 0), 255,
                               0).astype(np.uint8)
    hole_contours, _ = cv2.findContours(hole_candidates, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
    image_center = np.array(outer_ellipse[0], dtype=np.float32)
    candidate = None
    candidate_score = None
    for contour in hole_contours:
        area = cv2.contourArea(contour)
        if area < binary.size * 0.005 or len(contour) < 5:
            continue
        moments = cv2.moments(contour)
        if moments["m00"] <= 0:
            continue
        center = np.array([
            moments["m10"] / moments["m00"],
            moments["m01"] / moments["m00"],
        ], dtype=np.float32)
        score = np.linalg.norm(center - image_center) / max(area**0.5, 1.0)
        if candidate_score is None or score < candidate_score:
            candidate = contour
            candidate_score = score

    ellipse = cv2.fitEllipse(candidate) if candidate is not None else None
    if _is_plausible_inner_ellipse(ellipse, outer_ellipse):
        return ellipse
    recovered = _inner_ellipse_from_radial_edges(binary, outer_ellipse)
    if recovered is not None:
        logger.warning(
            "recovered circle config inner ellipse: rejected=%s recovered=%s",
            ellipse, recovered)
    return recovered


def get_circle_config_by_mask(mask):
    # 获取圆参数
    # showImage(mask)
    if isinstance(mask, Image.Image):
        mask = np.array(mask)
    mask = np.asarray(mask)
    if mask.ndim < 2 or mask.shape[0] == 0 or mask.shape[1] == 0:
        raise ValueError(f"invalid mask shape for circle config: {getattr(mask, 'shape', None)}")
    if mask.ndim == 3:
        mask = np.max(mask, axis=2)
    if mask.dtype != np.uint8:
        mask = np.clip(np.nan_to_num(mask, nan=0), 0, 255).astype(np.uint8)

    recovered_ellipse = get_inner_ellipse_by_mask(mask)
    if recovered_ellipse is not None:
        (center_x, center_y), (ellipse_width,
                               ellipse_height), _ = recovered_ellipse
        return {
            "inner_circle": {
                "circlex": [
                    int(center_x),
                    int(center_y),
                    int(max(ellipse_width, ellipse_height) / 2),
                ],
                "ellipse": recovered_ellipse,
                "inner_circle": [
                    (center_x, center_y),
                    min(ellipse_width, ellipse_height) / 2,
                ],
            }
        }

    def _fallback_circle_config(reason):
        height, width = mask.shape[:2]
        radius = max(min(width, height) / 2, 1.0)
        center = (width / 2, height / 2)
        ellipse = (center, (radius * 2, radius * 2), 0.0)
        logger.warning("circle config fallback: %s shape=%s", reason, mask.shape)
        return {
            "inner_circle": {
                "circlex": [int(center[0]), int(center[1]), int(radius)],
                "ellipse": ellipse,
                "inner_circle": [center, radius]
            }
        }

    mask = cv2.bitwise_not(mask)
    # 找到轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    image_center = (mask.shape[1] // 2, mask.shape[0] // 2)

    closest_contour = None
    min_distance = float('inf')

    for contour in contours:
        # 获取轮廓的外接矩形
        x, y, w, h = cv2.boundingRect(contour)
        # 计算矩形中心
        rect_center = (x + w // 2, y + h // 2)
        if h * w < (mask.shape[1] / 5) * (mask.shape[1] / 5):
            continue
        # 计算矩形中心与图像中心的距离
        distance = np.sqrt((rect_center[0] - image_center[0]) ** 2 + (rect_center[1] - image_center[1]) ** 2)
        # 找到最接近图像中心的轮廓
        if distance < min_distance:
            min_distance = distance
            closest_contour = contour
    if closest_contour is None:
        return _fallback_circle_config("no valid contour")
    (circlexX, circlexY), circlexRadius = cv2.minEnclosingCircle(closest_contour)
    rect = cv2.minAreaRect(closest_contour)
    (box_x, box_y), (box_w, box_h), box_angle = rect

    # 计算内接圆（在最小包围矩形中）
    inner_circle_radius = min(box_w, box_h) / 2
    inner_circle_center = (box_x, box_y)
    if len(closest_contour) >= 5:
        ellipse = cv2.fitEllipse(closest_contour)
    else:
        ellipse = (inner_circle_center, (inner_circle_radius * 2, inner_circle_radius * 2), box_angle)

    return {
        "inner_circle": {
            "circlex": [int(circlexX), int(circlexY), int(circlexRadius)],
            "ellipse": ellipse,
            "inner_circle": [inner_circle_center, inner_circle_radius]
        }
    }


def get_intersection_points(p1, p2, width, height):
    """
    获取两条线段的交点
    :return: 交点列表
    """
    x1, y1 = p1
    x2, y2 = p2

    intersection_points = []

    def add_point_if_on_boundary(x, y):
        if 0 <= x <= width and 0 <= y <= height:
            intersection_points.append(Point2D(int(x), int(y)))

    if x1 != x2 and y1 != y2:
        # 计算斜率和截距
        m = (y2 - y1) / (x2 - x1)
        c = y1 - m * x1

        # 求与上边界的交点 (y = 0)
        x_top = (0 - c) / m
        add_point_if_on_boundary(x_top, 0)

        # 求与下边界的交点 (y = height)
        x_bottom = (height - c) / m
        add_point_if_on_boundary(x_bottom, height)

        # 求与左边界的交点 (x = 0)
        y_left = m * 0 + c
        add_point_if_on_boundary(0, y_left)

        # 求与右边界的交点 (x = width)
        y_right = m * width + c
        add_point_if_on_boundary(width, y_right)
    elif x1 == x2:
        # 线垂直时，只会与上下边界相交
        add_point_if_on_boundary(x1, 0)
        add_point_if_on_boundary(x1, height)
    elif y1 == y2:
        # 线水平时，只会与左右边界相交
        add_point_if_on_boundary(0, y1)
        add_point_if_on_boundary(width, y1)
    unique_points = []
    seen_points = set()
    for p in intersection_points:
        if p[0] < 0:
            p[0] = 0
        if p[1] < 0:
            p[1] = 0
        if p[0] >= width:
            p[0] = width - 1
        if p[1] >= height:
            p[1] = height - 1

        point_key = (p[0], p[1])
        if point_key in seen_points:
            continue
        seen_points.add(point_key)
        unique_points.append(p)

    if len(unique_points) <= 2:
        return unique_points

    max_pair = unique_points[:2]
    max_distance = -1
    for index, p1_ in enumerate(unique_points):
        for p2_ in unique_points[index + 1:]:
            distance = (p1_[0] - p2_[0]) ** 2 + (p1_[1] - p2_[1]) ** 2
            if distance > max_distance:
                max_distance = distance
                max_pair = [p1_, p2_]
    return max_pair

def bound_box(box, image_size):
    """
    判断数组是否越界
    Args:
        box:
        image_size:

    Returns:

    """
    x,y,w,h = box
    width, height = image_size
    if x <0 or y < 0 or width <w+x or height< y+h:
        return True
    return False

def expansion_box(box, image_size, expand_factor=0.1,min_size=10,max_size=100):
    """
    扩展矩形框，使其尺寸增加一定比例，保持在图像尺寸内。

    参数:
    - box: 原始矩形框 (x, y, w, h)
    - image_size: 图像的尺寸 (width, height)
    - expand_factor: 扩展因子，控制扩展比例

    返回:
    - 扩展后的矩形框 (x, y, w, h)
    """
    x, y, w, h = box
    width, height = image_size

    # 计算扩展的尺寸
    if expand_factor==0:
        expand_w=0
        expand_h=0
    else:
        expand_w = max(min_size,min(max_size,w * expand_factor))
        expand_h = max(min_size,min(max_size,h * expand_factor))

    # 计算新的矩形位置和尺寸
    new_x = max(x - expand_w, 0)
    new_y = max(y - expand_h, 0)
    new_w = min(w + 2 * expand_w, width - new_x)
    new_h = min(h + 2 * expand_h, height - new_y)

    return int(new_x), int(new_y), int(new_w), int(new_h)
