"""
操作日志服务：为关键业务操作写入审计日志。

说明：
- add_log 仅把日志对象加入当前会话，由业务代码在 commit 时一并提交，
  保证"日志记录"与"业务成功"保持一致；业务失败回滚时日志同步回滚。
"""
from flask import request

from app.models import OperationLog


def _client_ip() -> str:
    """尽量获取客户端真实 IP，取不到时返回空字符串。"""
    if request:
        return request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or ""
    return ""


def add_log(action: str, target: str = "", detail: str = "", user=None) -> OperationLog:
    """写入一条操作日志。

    :param action: 操作类型，如 login / enter / exit / create / update / delete / export
    :param target: 操作对象，如 车牌号、用户名、规则名称
    :param detail: 操作详情，简短描述
    :param user:   当前用户对象（User），可为 None（如登录失败等场景）
    """
    log = OperationLog(
        user_id=user.id if user else None,
        username=user.username if user else "系统",
        action=action,
        target=target or "",
        detail=detail or "",
        ip=_client_ip(),
    )
    from app import db
    db.session.add(log)
    return log
