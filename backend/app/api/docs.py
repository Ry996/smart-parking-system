"""接口文档接口（实验二：RESTful 接口文档化）。

    GET /api/openapi.json   OpenAPI 3.0 规范，可直接导入 Swagger UI / Postman / Apifox
    GET /api/docs           在线接口文档页（零外部依赖，断网也能打开）

文档内容由 app/utils/openapi.py 反射 Flask 路由自动生成，
只要新增接口就自动出现在文档里，避免手工维护文档与代码不一致。
"""
from flask import Blueprint, Response, current_app, jsonify, request

from app.utils.openapi import build_openapi_spec, render_docs_html

docs_bp = Blueprint("docs", __name__)


def _server_url() -> str:
    return request.host_url.rstrip("/")


@docs_bp.route("/openapi.json", methods=["GET"])
def openapi_json():
    """输出 OpenAPI 3.0 规范。"""
    return jsonify(build_openapi_spec(current_app, server_url=_server_url()))


@docs_bp.route("/docs", methods=["GET"])
def docs_page():
    """在线接口文档页。"""
    spec = build_openapi_spec(current_app, server_url=_server_url())
    return Response(render_docs_html(spec), content_type="text/html; charset=utf-8")
