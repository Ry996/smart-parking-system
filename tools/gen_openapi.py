"""生成接口文档产物。

用法（在项目根目录执行）：

    python tools/gen_openapi.py

输出：
    docs/openapi.json   OpenAPI 3.0 规范，可导入 Swagger UI / Postman / Apifox
    docs/API.md         Markdown 版接口表，可直接贴进实验报告

文档内容反射自 Flask 路由与视图函数 docstring，
新增接口后重新执行本脚本即可，不用手工维护。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import create_app  # noqa: E402
from app.utils.openapi import build_openapi_spec, dump_spec, render_docs_markdown  # noqa: E402


def main() -> int:
    app = create_app()
    spec = build_openapi_spec(app, server_url="http://localhost:5000")

    docs_dir = ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)

    json_path = docs_dir / "openapi.json"
    md_path = docs_dir / "API.md"

    json_path.write_text(dump_spec(spec), encoding="utf-8")
    md_path.write_text(render_docs_markdown(spec), encoding="utf-8")

    operation_count = sum(len(operations) for operations in spec["paths"].values())
    secured = sum(
        1
        for operations in spec["paths"].values()
        for operation in operations.values()
        if operation.get("security")
    )

    print(f"已生成：{json_path}")
    print(f"已生成：{md_path}")
    print(f"接口路径 {len(spec['paths'])} 条，操作 {operation_count} 个，需登录 {secured} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
