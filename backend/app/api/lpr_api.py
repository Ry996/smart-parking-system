import logging
import os
import random
import string
import uuid

from flask import Blueprint, current_app, jsonify, request

from app.utils.auth import token_required
from app.utils.lpr import recognize_plate

lpr_bp = Blueprint("lpr", __name__)
logger = logging.getLogger(__name__)

PROVINCES = [
    "京", "津", "沪", "渝", "冀", "豫", "云", "辽", "黑", "湘",
    "皖", "鲁", "新", "苏", "浙", "赣", "鄂", "桂", "甘", "晋",
    "蒙", "陕", "吉", "闽", "贵", "粤", "川", "青", "琼", "宁",
]


def _mock_recognize() -> dict:
    province = random.choice(PROVINCES)
    city_code = random.choice(string.ascii_uppercase.replace("I", "").replace("O", ""))
    chars = string.digits + string.ascii_uppercase.replace("I", "").replace("O", "")
    suffix = "".join(random.choices(chars, k=5))
    return {
        "plate": f"{province}{city_code}{suffix}",
        "plate_type": "blue",
        "confidence": round(random.uniform(0.9, 0.99), 4),
        "error": None,
        "mode": "mock",
    }


@lpr_bp.route("/recognize", methods=["POST"])
@token_required
def recognize(current_user):
    if current_app.config.get("LPR_MOCK_MODE", True):
        return jsonify({"code": 200, "msg": "模拟识别成功", "data": _mock_recognize()})

    if "image" not in request.files:
        return jsonify({"code": 400, "msg": "请上传车牌图片。"}), 400

    file = request.files["image"]
    if not file or not file.filename:
        return jsonify({"code": 400, "msg": "请上传车牌图片。"}), 400

    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    image_path = os.path.join(upload_dir, filename)
    file.save(image_path)

    result = recognize_plate(image_path)
    logger.info("LPR result for %s: %s", image_path, result.get("plate"))

    if result["error"]:
        return jsonify({"code": 422, "msg": result["error"], "data": result}), 422

    return jsonify({"code": 200, "msg": "识别成功", "data": result})


@lpr_bp.route("/mode", methods=["GET"])
@token_required
def get_mode(current_user):
    mock_mode = current_app.config.get("LPR_MOCK_MODE", True)
    return jsonify({
        "code": 200,
        "data": {
            "mode": "mock" if mock_mode else "real",
            "label": "模拟识别" if mock_mode else "真实识别",
        },
    })
