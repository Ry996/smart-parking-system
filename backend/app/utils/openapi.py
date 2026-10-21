"""OpenAPI 3.0 文档生成器。

不引入额外依赖：直接反射 Flask 的 url_map、视图函数 docstring 和鉴权装饰器元数据，
生成可被 Swagger UI / Postman / Apifox 导入的标准规范，同时输出 Markdown 版接口表。

对应实验二「前后端分离与 RESTful API」中的接口文档要求。
"""
import html
import json
import re

PARAM_RE = re.compile(r"<(?:(\w+):)?(\w+)>")

TAG_LABELS = {
    "auth":         "认证",
    "parking":      "停车业务",
    "records":      "停车记录",
    "stats":        "数据统计",
    "fee_rules":    "收费规则",
    "users":        "用户管理",
    "lpr":          "车牌识别",
    "monthly":      "月租管理",
    "reservation":  "车位预约",
    "reservations": "车位预约",
    "blacklist":    "黑名单",
    "logs":         "操作日志",
    "export":       "数据导出",
    "ai":           "AI 能力",
    "roles":        "角色权限",
}

# 不属于业务接口、无需进文档的路由
EXCLUDED_PREFIXES = ("/api/openapi.json", "/api/docs")

TYPE_MAP = {
    "int":    {"type": "integer", "format": "int64"},
    "float":  {"type": "number", "format": "double"},
    "path":   {"type": "string"},
    "string": {"type": "string"},
}


def _split_doc(docstring):
    """docstring 首行作 summary，其余作 description。"""
    if not docstring:
        return "", ""
    lines = [line.rstrip() for line in docstring.strip().splitlines()]
    summary = lines[0].strip() if lines else ""
    description = "\n".join(lines[1:]).strip()
    return summary, description


def _path_parameters(rule_path):
    parameters = []
    for converter, name in PARAM_RE.findall(rule_path):
        schema = dict(TYPE_MAP.get(converter or "string", {"type": "string"}))
        parameters.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": schema,
                "description": f"路径参数 {name}",
            }
        )
    return parameters


def _request_body(rule_path, method):
    if method not in ("POST", "PUT", "PATCH"):
        return None
    if rule_path.startswith("/api/lpr/recognize"):
        return {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {"image": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    return {
        "required": False,
        "content": {
            "application/json": {
                "schema": {"type": "object", "additionalProperties": True},
            }
        },
    }


def _responses(method, auth_meta):
    responses = {
        "200": {
            "description": "业务处理完成（具体成功或业务失败以响应体 code 为准）",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiResponse"}}},
        }
    }
    if method in ("POST", "PUT", "PATCH"):
        responses["400"] = {"description": "参数校验失败"}
    if auth_meta.get("auth"):
        responses["401"] = {"description": "未提供 Token 或 Token 失效"}
        responses["403"] = {"description": "权限不足"}
    responses["422"] = {"description": "业务规则不满足（如车牌识别失败）"}
    responses["429"] = {"description": "请求过于频繁（AI 接口限流）"}
    return responses


def build_openapi_spec(app, server_url: str = "http://localhost:5000") -> dict:
    """从 Flask 应用反射生成 OpenAPI 3.0 规范。"""
    paths = {}
    tags_seen = {}

    for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
        rule_path = rule.rule
        if not rule_path.startswith("/api") or rule_path.startswith(EXCLUDED_PREFIXES):
            continue
        view = app.view_functions.get(rule.endpoint)
        if view is None:
            continue

        methods = sorted(m for m in (rule.methods or set()) if m not in ("HEAD", "OPTIONS"))
        if not methods:
            continue

        blueprint = rule.endpoint.split(".", 1)[0] if "." in rule.endpoint else "default"
        tag = TAG_LABELS.get(blueprint, blueprint)
        tags_seen[tag] = blueprint

        auth_meta = getattr(view, "__auth_meta__", {}) or {}
        summary, description = _split_doc(view.__doc__)
        parameters = _path_parameters(rule_path)

        for method in methods:
            operation = {
                "summary": summary or f"{method} {rule_path}",
                "operationId": f"{rule.endpoint}_{method.lower()}",
                "tags": [tag],
                "parameters": parameters,
                "responses": _responses(method, auth_meta),
            }
            if description:
                operation["description"] = description
            if auth_meta.get("auth"):
                operation["security"] = [{"bearerAuth": []}]
            if auth_meta.get("permission"):
                operation["description"] = (
                    (operation.get("description", "") + "\n\n").strip()
                    + f"所需权限：`{auth_meta['permission']}`"
                )
            elif auth_meta.get("role"):
                operation["description"] = (
                    (operation.get("description", "") + "\n\n").strip()
                    + f"所需角色：`{auth_meta['role']}`"
                )

            body = _request_body(rule_path, method)
            if body:
                operation["requestBody"] = body

            paths.setdefault(rule_path, {})[method.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "智慧停车场管理系统 API",
            "version": "2.2.0",
            "description": (
                "V2.2 在 V2.1 基础上补齐：RBAC 角色权限、提示注入防护、"
                "RAG 知识库问答、AI 调用留痕与人工复核反馈。\n\n"
                "所有业务接口统一返回 `{code, msg, data}`；认证方式为 "
                "`Authorization: Bearer <token>`。"
            ),
        },
        "servers": [{"url": server_url, "description": "本地开发环境"}],
        "tags": [{"name": label} for label in sorted(tags_seen)],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            "schemas": {
                "ApiResponse": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer", "example": 200},
                        "msg": {"type": "string"},
                        "data": {},
                    },
                }
            },
        },
        "paths": paths,
    }


def render_docs_markdown(spec: dict) -> str:
    """把规范渲染成 Markdown 接口文档，便于放进实验报告。"""
    lines = [f"# {spec['info']['title']}", "", spec["info"]["description"], ""]
    lines.append(f"- 版本：{spec['info']['version']}")
    lines.append(f"- 服务地址：{spec['servers'][0]['url']}")
    lines.append("- 认证：`Authorization: Bearer <token>`")
    lines.append("")
    lines.append("> 本文档由 `tools/gen_openapi.py` 从 Flask 路由自动生成，改代码后重新生成即可。")
    lines.append("")

    grouped = {}
    for path, operations in sorted(spec["paths"].items()):
        for method, operation in operations.items():
            tag = operation["tags"][0]
            grouped.setdefault(tag, []).append((path, method.upper(), operation))

    for tag in sorted(grouped):
        lines.append(f"## {tag}")
        lines.append("")
        lines.append("| 方法 | 路径 | 说明 | 鉴权 |")
        lines.append("| --- | --- | --- | --- |")
        for path, method, operation in grouped[tag]:
            auth = "公开"
            if operation.get("security"):
                auth = "Bearer"
            summary = operation.get("summary", "").replace("|", "\\|")
            lines.append(f"| {method} | `{path}` | {summary} | {auth} |")
        lines.append("")

        for path, method, operation in grouped[tag]:
            lines.append(f"### {method} {path}")
            lines.append("")
            lines.append(operation.get("summary", ""))
            if operation.get("description"):
                lines.append("")
                lines.append(operation["description"])
            if operation.get("parameters"):
                lines.append("")
                lines.append("路径参数：" + "、".join(
                    f"`{p['name']}`({p['schema'].get('type', 'string')})" for p in operation["parameters"]
                ))
            lines.append("")

    return "\n".join(lines)


def dump_spec(spec: dict) -> str:
    return json.dumps(spec, ensure_ascii=False, indent=2)


def render_docs_html(spec: dict) -> str:
    """生成零依赖的接口文档页（无需 CDN，断网也能看）。"""
    escaped_title = html.escape(spec["info"]["title"])
    payload = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escaped_title}</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    background: radial-gradient(900px 420px at 85% -10%, rgba(56,189,248,.08), transparent 60%),
                linear-gradient(180deg, #0b1220 0%, #0d1b2e 100%);
    color: #e2e8f0; padding: 28px 32px 64px;
  }}
  h1 {{ font-size: 24px; margin: 0 0 6px; }}
  .muted {{ color: #94a3b8; font-size: 13px; line-height: 1.7; }}
  .toolbar {{ display: flex; gap: 12px; align-items: center; margin: 20px 0; flex-wrap: wrap; }}
  input {{
    flex: 1; min-width: 240px; padding: 10px 14px; border-radius: 10px;
    border: 1px solid rgba(148,163,184,.25); background: rgba(15,30,51,.9); color: #e2e8f0;
  }}
  a.btn {{
    padding: 10px 16px; border-radius: 10px; text-decoration: none; color: #04121f; font-weight: 700;
    background: linear-gradient(135deg, #38bdf8, #818cf8);
  }}
  .tag-title {{ margin: 26px 0 10px; font-size: 16px; color: #cfefff; }}
  .row {{
    display: grid; grid-template-columns: 74px 1fr auto; gap: 12px; align-items: center;
    padding: 11px 14px; border-radius: 10px; margin-bottom: 7px;
    background: rgba(15,30,51,.72); border: 1px solid rgba(148,163,184,.12);
  }}
  .row:hover {{ border-color: rgba(56,189,248,.45); }}
  .method {{ font-weight: 800; font-size: 12px; letter-spacing: .5px; text-align: center;
             padding: 4px 0; border-radius: 6px; }}
  .GET {{ background: rgba(34,197,94,.18); color: #86efac; }}
  .POST {{ background: rgba(56,189,248,.18); color: #7dd3fc; }}
  .PUT {{ background: rgba(245,158,11,.18); color: #fcd34d; }}
  .DELETE {{ background: rgba(248,113,113,.18); color: #fca5a5; }}
  .path {{ font-family: Consolas, monospace; font-size: 13px; }}
  .sum {{ color: #94a3b8; font-size: 12px; margin-top: 3px; }}
  .lock {{ font-size: 12px; color: #fbbf24; white-space: nowrap; }}
  .perm {{ font-size: 11px; color: #a78bfa; }}
</style>
</head>
<body>
  <h1>{escaped_title}</h1>
  <div class="muted">
    版本 {html.escape(spec['info']['version'])} · 服务地址 {html.escape(spec['servers'][0]['url'])}<br/>
    认证：<code>Authorization: Bearer &lt;token&gt;</code> · 统一响应：<code>{{code, msg, data}}</code>
  </div>
  <div class="toolbar">
    <input id="q" placeholder="搜索路径 / 说明，例如 parking、登录、权限" />
    <a class="btn" href="/api/openapi.json" target="_blank">查看 openapi.json</a>
  </div>
  <div id="list"></div>

<script>
const spec = {payload};
const labels = {{}};
(spec.tags || []).forEach(t => labels[t.name] = t.name);

function render(keyword) {{
  const list = document.getElementById('list');
  list.innerHTML = '';
  const kw = (keyword || '').trim().toLowerCase();
  const grouped = {{}};

  Object.entries(spec.paths).forEach(([path, ops]) => {{
    Object.entries(ops).forEach(([method, op]) => {{
      const tag = (op.tags && op.tags[0]) || '其他';
      const haystack = (path + ' ' + method + ' ' + (op.summary || '')).toLowerCase();
      if (kw && !haystack.includes(kw)) return;
      (grouped[tag] = grouped[tag] || []).push([path, method, op]);
    }});
  }});

  Object.keys(grouped).sort().forEach(tag => {{
    const title = document.createElement('div');
    title.className = 'tag-title';
    title.textContent = tag;
    list.appendChild(title);

    grouped[tag].forEach(([path, method, op]) => {{
      const row = document.createElement('div');
      row.className = 'row';
      const needsAuth = !!(op.security && op.security.length);
      const perm = (op.description || '').match(/所需(?:权限|角色)：`([^`]+)`/);
      row.innerHTML =
        '<div class="method ' + method.toUpperCase() + '">' + method.toUpperCase() + '</div>' +
        '<div><div class="path">' + path + '</div><div class="sum">' + (op.summary || '') + '</div></div>' +
        '<div>' + (needsAuth ? '<div class="lock">🔒 需登录</div>' : '<div class="lock" style="color:#64748b">公开</div>') +
        (perm ? '<div class="perm">' + perm[1] + '</div>' : '') + '</div>';
      list.appendChild(row);
    }});
  }});

  if (!list.children.length) {{
    list.innerHTML = '<div class="muted">没有匹配的接口。</div>';
  }}
}}

document.getElementById('q').addEventListener('input', e => render(e.target.value));
render('');
</script>
</body>
</html>"""
