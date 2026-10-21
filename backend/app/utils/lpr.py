"""License plate recognition using HyperLPR3 with multiple preprocessing variants."""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache

try:  # noqa: SIM105
    import cv2
    import numpy as np
    from PIL import Image, ImageOps

    IMAGE_DEPS_ERROR = None
except Exception as _exc:  # 依赖缺失或 NumPy/OpenCV 版本不兼容时优雅降级
    cv2 = None
    np = None
    Image = None
    ImageOps = None
    IMAGE_DEPS_ERROR = _exc


logger = logging.getLogger(__name__)

PROVINCE_CHARS = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青琼宁藏使领警学港澳"
ALNUM_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
PLATE_SEPARATORS = "·.・-—_ "

NORMAL_PLATE_RE = re.compile(rf"^[{PROVINCE_CHARS}][A-Z][{ALNUM_CHARS}]{{5}}$")
NEW_ENERGY_SMALL_RE = re.compile(rf"^[{PROVINCE_CHARS}][A-Z][DF][{ALNUM_CHARS}]{{5}}$")
NEW_ENERGY_LARGE_RE = re.compile(rf"^[{PROVINCE_CHARS}][A-Z][{ALNUM_CHARS}]{{5}}[DF]$")

PLATE_TYPE_MAP = {
    0: "blue",
    1: "green",
    2: "yellow",
    3: "green",
    4: "blue",
    5: "yellow",
    6: "blue",
    7: "blue",
    8: "yellow",
    9: "yellow",
}


def _decode_image(image_path: str) -> np.ndarray:
    """Load an image with Pillow so local paths and EXIF rotation are handled reliably."""
    try:
        with Image.open(image_path) as image:
            normalized = ImageOps.exif_transpose(image).convert("RGB")
            rgb = np.array(normalized)
    except Exception as exc:
        raise ValueError("图片读取失败，请确认上传的是有效图片文件。") from exc

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """Resize very large images to keep recognition responsive."""
    height, width = image.shape[:2]
    max_edge = max(height, width)
    if max_edge <= 1600:
        return image

    scale = 1600 / max_edge
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def _is_closeup_plate_image(image: np.ndarray) -> bool:
    height, width = image.shape[:2]
    if height == 0:
        return False
    ratio = width / height
    return 2.4 <= ratio <= 4.4 and height <= 220


def _add_padding(image: np.ndarray, size: int, color: int) -> np.ndarray:
    return cv2.copyMakeBorder(
        image,
        size,
        size,
        size,
        size,
        borderType=cv2.BORDER_CONSTANT,
        value=(color, color, color),
    )


def _generate_variants(image: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """Generate several image variants to improve recognition success."""
    variants: list[tuple[str, np.ndarray]] = [("original", image)]
    closeup_plate = _is_closeup_plate_image(image)

    height, width = image.shape[:2]
    max_edge = max(height, width)
    if max_edge < 1200:
        enlarged = cv2.resize(image, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        variants.append(("enlarged", enlarged))
    if closeup_plate:
        enlarged_2x = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        enlarged_3x = cv2.resize(image, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_LANCZOS4)
        variants.append(("closeup_2x", enlarged_2x))
        variants.append(("closeup_3x", enlarged_3x))
        variants.append(("closeup_white_pad", _add_padding(enlarged_2x, 24, 255)))
        variants.append(("closeup_black_pad", _add_padding(enlarged_2x, 24, 0)))

        denoised = cv2.bilateralFilter(image, 7, 60, 60)
        denoised_2x = cv2.resize(denoised, None, fx=2.2, fy=2.2, interpolation=cv2.INTER_CUBIC)
        variants.append(("closeup_denoised", denoised_2x))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    variants.append(("gray", gray_bgr))

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    variants.append(("clahe", cv2.cvtColor(clahe, cv2.COLOR_GRAY2BGR)))

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    sharp = cv2.addWeighted(gray, 1.6, blurred, -0.6, 0)
    variants.append(("sharp", cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)))

    alpha = 1.25
    beta = 10
    contrast = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    variants.append(("contrast", contrast))

    if not closeup_plate:
        x1 = int(width * 0.12)
        x2 = int(width * 0.88)
        y1 = int(height * 0.45)
        y2 = int(height * 0.88)
        if x2 > x1 and y2 > y1:
            roi = image[y1:y2, x1:x2]
            if roi.size:
                variants.append(("roi", roi))
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                roi_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(roi_gray)
                variants.append(("roi_clahe", cv2.cvtColor(roi_clahe, cv2.COLOR_GRAY2BGR)))
                roi_enlarged = cv2.resize(roi, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
                variants.append(("roi_enlarged", roi_enlarged))

    unique_variants: list[tuple[str, np.ndarray]] = []
    seen_signatures: set[tuple[int, int, int, int]] = set()
    for name, variant in variants:
        signature = (
            variant.shape[0],
            variant.shape[1],
            variant.shape[2] if variant.ndim == 3 else 1,
            int(float(variant.mean())),
        )
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        unique_variants.append((name, variant))
    return unique_variants


@lru_cache(maxsize=1)
def _get_catcher():
    if IMAGE_DEPS_ERROR is not None:
        raise ImportError(
            f"图像识别依赖不可用（{IMAGE_DEPS_ERROR}），可设置 LPR_MOCK_MODE=true 使用模拟识别。"
        )
    try:
        import hyperlpr3 as lpr3
    except ImportError as exc:
        raise ImportError("未安装 hyperlpr3，请先完成后端依赖安装。") from exc

    return lpr3.LicensePlateCatcher(detect_level=lpr3.DETECT_LEVEL_HIGH)


def _normalize_plate_code(code: str) -> str:
    cleaned = (code or "").strip().upper()
    for sep in PLATE_SEPARATORS:
        cleaned = cleaned.replace(sep, "")
    return cleaned


def _match_plate_pattern(code: str) -> bool:
    if not code:
        return False
    return bool(
        NORMAL_PLATE_RE.fullmatch(code)
        or NEW_ENERGY_SMALL_RE.fullmatch(code)
        or NEW_ENERGY_LARGE_RE.fullmatch(code)
    )


def _repair_plate_code(code: str) -> str:
    normalized = _normalize_plate_code(code)
    if len(normalized) < 2:
        return normalized

    chars = list(normalized)
    city_map = {"0": "D", "1": "I", "2": "Z", "5": "S", "6": "G", "7": "T", "8": "B"}
    if chars[1] in city_map:
        chars[1] = city_map[chars[1]]

    repaired = "".join(chars)
    if len(repaired) >= 3 and repaired[2] == "O":
        repaired = repaired[:2] + "0" + repaired[3:]
    return repaired


def _plate_field(plate, key: str, default=None):
    if isinstance(plate, dict):
        return plate.get(key, default)

    if isinstance(plate, (list, tuple)):
        field_map = {
            "plate_code": 0,
            "rec_confidence": 1,
            "plate_type": 2,
            "det_bound_box": 3,
        }
        index = field_map.get(key)
        if index is not None and len(plate) > index:
            return plate[index]
        return default

    return getattr(plate, key, default)


def _plate_score(plate) -> float:
    rec = float(_plate_field(plate, "rec_confidence", 0.0) or 0.0)
    raw_code = str(_plate_field(plate, "plate_code", "") or "").strip()
    code = _repair_plate_code(raw_code)
    length_bonus = 0.12 if len(code) in (7, 8) else -0.2
    province_bonus = 0.12 if code and code[0] in PROVINCE_CHARS else -0.25
    format_bonus = 0.35 if _match_plate_pattern(code) else -0.45
    return rec * 0.75 + length_bonus + province_bonus + format_bonus


def _best_plate(results) -> object | None:
    if not results:
        return None
    return max(results, key=_plate_score)


def _map_plate_type(raw_plate_type: int | None) -> str:
    return PLATE_TYPE_MAP.get(raw_plate_type, "blue")


def _plate_debug_info(plate) -> dict:
    raw_code = str(_plate_field(plate, "plate_code", "") or "")
    repaired_code = _repair_plate_code(raw_code)
    return {
        "code": raw_code,
        "normalized_code": repaired_code,
        "rec_confidence": round(float(_plate_field(plate, "rec_confidence", 0.0) or 0.0), 4),
        "det_confidence": None,
        "plate_type": _plate_field(plate, "plate_type", None),
        "pattern_ok": _match_plate_pattern(repaired_code),
        "score": round(_plate_score(plate), 4),
    }


def recognize_plate(image_path: str) -> dict:
    if not image_path or not os.path.exists(image_path):
        return {
            "plate": None,
            "confidence": 0.0,
            "plate_type": None,
            "error": "未找到上传的图片文件。",
        }

    if IMAGE_DEPS_ERROR is not None:
        # 依赖不可用时不让主业务崩溃，交给前端走手动录入兜底
        return {
            "plate": None,
            "confidence": 0.0,
            "plate_type": None,
            "error": f"车牌识别依赖不可用（{IMAGE_DEPS_ERROR}），请手动录入车牌或开启 LPR_MOCK_MODE。",
        }

    try:
        catcher = _get_catcher()
        image = _preprocess_image(_decode_image(image_path))
        logger.warning("LPR start: path=%s shape=%s", image_path, image.shape)

        best = None
        best_variant = None

        for variant_name, variant in _generate_variants(image):
            plates = catcher(variant)
            logger.warning("LPR variant=%s shape=%s candidates=%s", variant_name, variant.shape, len(plates))
            for index, plate in enumerate(plates):
                logger.warning("LPR variant=%s candidate_%s=%s", variant_name, index, _plate_debug_info(plate))

            candidate = _best_plate(plates)
            if candidate and (best is None or _plate_score(candidate) > _plate_score(best)):
                best = candidate
                best_variant = variant_name

        if not best:
            logger.warning("LPR failed: no valid plate detected for %s", image_path)
            return {
                "plate": None,
                "confidence": 0.0,
                "plate_type": None,
                "error": "尝试好几次，车牌识别结果为空，请更换图片后重试。",
            }

        plate_code = _repair_plate_code(str(_plate_field(best, "plate_code", "") or ""))
        best_score = _plate_score(best)
        if not plate_code:
            logger.warning("LPR failed: best candidate has empty code for %s", image_path)
            return {
                "plate": None,
                "confidence": 0.0,
                "plate_type": None,
                "error": "尝试好几次，车牌识别结果为空，请更换图片后重试。",
            }
        if not _match_plate_pattern(plate_code):
            logger.warning("LPR failed: invalid plate pattern variant=%s result=%s", best_variant, _plate_debug_info(best))
            return {
                "plate": None,
                "confidence": 0.0,
                "plate_type": None,
                "error": "识别到了疑似车牌，但格式不可靠，请调整角度、靠近镜头后重试。",
            }
        if best_score < 0.55:
            logger.warning("LPR failed: candidate score too low variant=%s score=%s result=%s", best_variant, round(best_score, 4), _plate_debug_info(best))
            return {
                "plate": None,
                "confidence": 0.0,
                "plate_type": None,
                "error": "识别结果可信度不足，请调整角度、光线或改用手动录入。",
            }

        logger.warning("LPR success: variant=%s result=%s", best_variant, _plate_debug_info(best))
        return {
            "plate": plate_code,
            "confidence": round(float(_plate_field(best, "rec_confidence", 0.0) or 0.0), 4),
            "plate_type": _map_plate_type(_plate_field(best, "plate_type", None)),
            "error": None,
        }
    except Exception as exc:
        logger.exception("LPR exception for %s", image_path)
        return {
            "plate": None,
            "confidence": 0.0,
            "plate_type": None,
            "error": str(exc),
        }
