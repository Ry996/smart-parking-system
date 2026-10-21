"""AI 能力接口：RAG 问答、模型状态、幻觉案例复核、知识库重建。

实验五（LLM 应用开发与智能功能原型）的可演示入口：
    POST /api/ai/ask         基于知识库的检索增强问答（带引用）
    GET  /api/ai/status      当前模型与知识库状态
    POST /api/ai/feedback    人工复核 AI 输出（沉淀幻觉/引用错误案例）
    GET  /api/ai/feedback    查看已沉淀的案例（报告素材）
    GET  /api/ai/calls       查看大模型调用留痕
    POST /api/ai/reindex     重建知识库向量索引

实验四（AI 安全）的落地体现：
    - 输入长度/字符校验（sanitize_text）
    - 提示注入识别与拦截（detect_prompt_injection），命中后不调用模型
    - 接口限流（SimpleRateLimiter）
"""
import logging

from flask import Blueprint, jsonify, request

from app import db
from app.models import AiCall, AiFeedback
from app.services import rag_service
from app.services.ai_service import REFUSAL_TEXT, ai_service
from app.services.log_service import add_log
from app.utils.auth import permission_required, token_required
from app.utils.security import (
    MAX_NOTE_LENGTH,
    SimpleRateLimiter,
    detect_prompt_injection,
    sanitize_text,
    truncate,
)

ai_bp = Blueprint("ai", __name__)
logger = logging.getLogger(__name__)

_rate_limiter = SimpleRateLimiter(limit=30, window_seconds=60)

BLOCKED_REPLY = (
    "检测到提示注入风险，该请求已被拦截。"
    "系统只根据停车场知识库回答业务问题，不会执行或泄露系统提示词、密钥与内部配置。"
)

FEEDBACK_CATEGORIES = {
    "hallucination":   "幻觉（编造资料中不存在的事实）",
    "wrong_citation":  "引用错误（引用编号与内容对不上）",
    "refusal":         "过度拒答（资料里有却回答无法确定）",
    "prompt_injection": "提示注入尝试",
    "other":           "其他问题",
}


@ai_bp.route("/status", methods=["GET"])
@token_required
def status(current_user):
    """查询大模型与知识库的当前状态。"""
    index = rag_service.ensure_index()
    return jsonify(
        {
            "code": 200,
            "data": {
                "enabled": ai_service.enabled,
                "provider": "deepseek" if ai_service.enabled else "offline",
                "model": ai_service.model if ai_service.enabled else None,
                "promptVersions": {
                    "rag_answer": "rag-v2",
                    "parking_advice": "advice-v2",
                    "general_answer": "general-v1",
                },
                "knowledge": index,
                "refusalText": REFUSAL_TEXT,
                "categories": FEEDBACK_CATEGORIES,
            },
        }
    )


@ai_bp.route("/ask", methods=["POST"])
@permission_required("ai:ask")
def ask(current_user):
    """基于知识库的 RAG 问答，答案带引用来源。"""
    if not _rate_limiter.allow(f"ai-ask:{current_user.id}"):
        return jsonify({"code": 429, "msg": "请求过于频繁，请稍后再试。"}), 429

    data = request.get_json(silent=True) or {}
    try:
        question = sanitize_text(data.get("question"), "问题", 300)
        top_k = max(1, min(int(data.get("top_k", rag_service.DEFAULT_TOP_K) or rag_service.DEFAULT_TOP_K), 8))
    except (TypeError, ValueError) as exc:
        return jsonify({"code": 400, "msg": str(exc)}), 400

    # 提示注入防护：命中即拦截，绝不把可疑内容送进模型
    reasons = detect_prompt_injection(question)
    if reasons:
        add_log(
            "ai_prompt_injection",
            current_user.username,
            f"拦截提示注入：{'、'.join(reasons)}",
            user=current_user,
        )
        db.session.commit()
        return jsonify(
            {
                "code": 200,
                "msg": "已拦截可疑请求",
                "data": {
                    "answer": BLOCKED_REPLY,
                    "mode": "BLOCKED",
                    "provider": "guard",
                    "blocked": True,
                    "refused": True,
                    "basedOnSources": False,
                    "sources": [],
                    "reasons": reasons,
                    "question": question,
                },
            }
        )

    sources = rag_service.search(question, top_k)

    if sources:
        answer, provider, refused = ai_service.answer_with_sources(question, sources)
        mode = "RAG"
    else:
        answer, provider = ai_service.answer_general(question)
        refused = False
        mode = "GENERAL"

    add_log(
        "ai_ask",
        current_user.username,
        f"{mode} 问答：{truncate(question, 60)}",
        user=current_user,
    )
    db.session.commit()

    return jsonify(
        {
            "code": 200,
            "data": {
                "answer": answer,
                "mode": mode,
                "provider": provider,
                "blocked": False,
                "refused": refused,
                "basedOnSources": bool(sources) and not refused,
                "sources": rag_service.public_sources(sources),
                "question": question,
                "promptVersion": "rag-v2" if sources else "general-v1",
            },
        }
    )


@ai_bp.route("/feedback", methods=["POST"])
@token_required
def create_feedback(current_user):
    """提交一条 AI 输出的人工复核记录（幻觉案例沉淀）。"""
    data = request.get_json(silent=True) or {}
    category = str(data.get("category") or "hallucination").strip()

    if category not in FEEDBACK_CATEGORIES:
        return jsonify({"code": 400, "msg": "不支持的反馈类型。"}), 400

    try:
        question = sanitize_text(data.get("question"), "问题", 300)
        note = sanitize_text(data.get("note") or "", "备注", MAX_NOTE_LENGTH) if data.get("note") else ""
    except ValueError as exc:
        return jsonify({"code": 400, "msg": str(exc)}), 400

    feedback = AiFeedback(
        question=question,
        answer=truncate(data.get("answer") or "", 4000),
        category=category,
        expected_answer=truncate(data.get("expected_answer") or "", 2000),
        note=note,
        mode=str(data.get("mode") or "")[:20],
        reporter=current_user.username,
    )
    db.session.add(feedback)
    add_log("ai_feedback", current_user.username, f"登记 AI 复核案例：{category}", user=current_user)
    db.session.commit()

    return jsonify({"code": 200, "msg": "案例已记录", "data": feedback.to_dict()})


@ai_bp.route("/feedback", methods=["GET"])
@permission_required("ai:feedback:read")
def list_feedback(current_user):
    """查看已沉淀的 AI 复核案例，可直接用于实验报告。"""
    category = request.args.get("category")
    query = AiFeedback.query
    if category:
        query = query.filter_by(category=category)

    rows = query.order_by(AiFeedback.id.desc()).limit(100).all()
    stats = {}
    for row in AiFeedback.query.all():
        stats[row.category] = stats.get(row.category, 0) + 1

    return jsonify(
        {
            "code": 200,
            "data": {
                "total": len(rows),
                "byCategory": stats,
                "categories": FEEDBACK_CATEGORIES,
                "items": [row.to_dict() for row in rows],
            },
        }
    )


@ai_bp.route("/calls", methods=["GET"])
@permission_required("ai:feedback:read")
def list_calls(current_user):
    """查看大模型调用留痕（模型、提示词版本、耗时、错误）。"""
    rows = AiCall.query.order_by(AiCall.id.desc()).limit(50).all()
    return jsonify(
        {
            "code": 200,
            "data": {
                "total": AiCall.query.count(),
                "items": [row.to_dict() for row in rows],
            },
        }
    )


@ai_bp.route("/reindex", methods=["POST"])
@permission_required("ai:manage")
def reindex(current_user):
    """重建知识库向量索引（修改 knowledge/*.md 后调用）。"""
    result = rag_service.rebuild_index()
    add_log("ai_reindex", current_user.username, f"重建索引：{result}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "索引重建完成", "data": result})
