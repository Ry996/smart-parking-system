"""轻量 RAG（检索增强生成）服务。

设计取舍：
- 不依赖外部 embedding 服务：用「中文二元组 + 稀疏 TF-IDF + 余弦相似度」做本地检索，
  离线、可复现、零额外依赖，符合课纲「RAG 入门」的教学目标；
- 知识库落在 knowledge_documents / knowledge_chunks 两张表，切块参数在线可调；
- 检索除相似度外还计算「查询覆盖率」——问题里的高信息量词有多大比例命中片段。
  只有相似度与覆盖率同时达标才认为「资料支持回答」，否则返回空结果，
  由上层回答「根据当前资料无法确定」，这是抑制 RAG 幻觉的关键一步。

流程：文档 → 切块 → 分词计数入库 → 提问分词 → TF-IDF 加权 → 余弦相似度排序
      → 覆盖率门控 → 取 TopK → 拼上下文。
"""
import json
import math
import re
from pathlib import Path

from app import db
from app.models import KnowledgeChunk, KnowledgeDocument

CHUNK_SIZE = 320
CHUNK_OVERLAP = 60
DEFAULT_TOP_K = 4

# 相似度门限：低于该值认为不相关（实测业务问题 0.14~0.38，无关问题 0.00~0.10）
MIN_SCORE = 0.12
# 覆盖率门限：问题中的高信息量词至少命中一半，才算「资料支持回答」
MIN_COVERAGE = 0.5
# IDF 达到该值视为高信息量词（在越少片段中出现，越有区分度）
INFORMATIVE_IDF = 1.2

_TOKEN_RE = re.compile(r"[\u4e00-\u9fa5]+|[A-Za-z]+|\d+")
_HEADING = re.compile(r"^\s*#\s*(.+?)\s*$", re.MULTILINE)


def _tokens(text: str) -> list:
    """中文按二元组切分（单字词组保留原样），英文与数字按词切分并转小写。"""
    tokens = []
    for match in _TOKEN_RE.finditer(text or ""):
        piece = match.group(0)
        if "\u4e00" <= piece[0] <= "\u9fa5":
            tokens.extend([piece[i:i + 2] for i in range(len(piece) - 1)] or [piece])
        else:
            tokens.append(piece.lower())
    return tokens


def _counts(text: str) -> dict:
    """词频统计：{token: count}。"""
    result = {}
    for token in _tokens(text):
        result[token] = result.get(token, 0) + 1
    return result


def _to_vector(counts: dict, idf: dict = None) -> dict:
    """词频（可选 IDF 加权）后做 L2 归一化，得到稀疏向量。"""
    idf = idf or {}
    weighted = {token: count * idf.get(token, 1.0) for token, count in counts.items()}
    norm = math.sqrt(sum(value * value for value in weighted.values()))
    if not norm:
        return {}
    return {token: value / norm for token, value in weighted.items()}


def vectorize(text: str, idf: dict = None) -> dict:
    """把文本映射为归一化的稀疏 TF-IDF 向量（字典表示 token -> 权重）。"""
    return _to_vector(_counts(text), idf)


def cosine(left: dict, right: dict) -> float:
    """稀疏向量余弦相似度。"""
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return float(sum(value * right.get(token, 0.0) for token, value in left.items()))


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """按窗口切块，优先在换行处断开，块间保留 overlap 字符的上下文。"""
    text = (text or "").strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            newline = text.rfind("\n", start + size // 2, end)
            if newline != -1:
                end = newline
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _read_markdown(path: Path):
    content = path.read_text(encoding="utf-8").strip()
    heading = _HEADING.search(content)
    title = heading.group(1) if heading else path.stem
    return title, content


def sync_documents_from_dir(knowledge_dir) -> int:
    """把 knowledge/*.md 同步进知识库表，按文件名（code）幂等更新。"""
    directory = Path(knowledge_dir)
    if not directory.is_dir():
        return 0

    changed = 0
    for path in sorted(directory.glob("*.md")):
        title, content = _read_markdown(path)
        code = path.stem
        document = KnowledgeDocument.query.filter_by(code=code).first()
        if document is None:
            document = KnowledgeDocument(code=code)
            db.session.add(document)
        document.title = title
        document.content = content
        document.category = "业务规则"
        changed += 1

    if changed:
        db.session.commit()
    return changed


def rebuild_index() -> dict:
    """重建全部知识片段的词频索引。"""
    if KnowledgeDocument.query.count() == 0:
        return {"documents": 0, "chunks": 0, "rebuilt": False}

    KnowledgeChunk.query.delete()
    db.session.commit()

    chunk_total = 0
    documents = KnowledgeDocument.query.order_by(KnowledgeDocument.id.asc()).all()
    for document in documents:
        pieces = chunk_text(document.content)
        document.chunk_count = len(pieces)
        for index, piece in enumerate(pieces):
            db.session.add(
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=piece,
                    embedding=json.dumps(_counts(piece), ensure_ascii=False),
                )
            )
            chunk_total += 1
    db.session.commit()
    return {"documents": len(documents), "chunks": chunk_total, "rebuilt": True}


def ensure_index() -> dict:
    """索引缺失时自动重建，避免部署后忘记建索引。"""
    if KnowledgeDocument.query.count() == 0:
        return {"documents": 0, "chunks": 0, "rebuilt": False}
    if KnowledgeChunk.query.count() == 0:
        return rebuild_index()
    return {
        "documents": KnowledgeDocument.query.count(),
        "chunks": KnowledgeChunk.query.count(),
        "rebuilt": False,
    }


def _parse_counts(raw) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _corpus_idf(chunks) -> dict:
    """按片段计算文档频率与 IDF，越少出现的词权重越高。"""
    total = len(chunks)
    document_frequency = {}
    for chunk in chunks:
        for token in _parse_counts(chunk.embedding):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    return {
        token: math.log((total + 1) / (frequency + 1)) + 1
        for token, frequency in document_frequency.items()
    }


def search(question: str, top_k: int = DEFAULT_TOP_K) -> list:
    """检索与问题最相关的知识片段；相似度或覆盖率不达标时返回空列表。"""
    ensure_index()

    chunks = KnowledgeChunk.query.all()
    if not chunks:
        return []

    idf = _corpus_idf(chunks)
    query_counts = _counts(question)
    if not query_counts:
        return []

    query_vector = _to_vector(query_counts, idf)
    informative = {token for token in query_counts if idf.get(token, 1.0) >= INFORMATIVE_IDF}
    documents = {document.id: document for document in KnowledgeDocument.query.all()}

    scored = []
    for chunk in chunks:
        counts = _parse_counts(chunk.embedding)
        if not counts:
            continue
        score = cosine(query_vector, _to_vector(counts, idf))
        coverage = len(informative & set(counts)) / len(informative) if informative else 0.0
        scored.append((score, coverage, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)

    results = []
    for score, coverage, chunk in scored[:top_k]:
        if score < MIN_SCORE or coverage < MIN_COVERAGE:
            continue
        document = documents.get(chunk.document_id)
        results.append(
            {
                "documentId": chunk.document_id,
                "title": document.title if document else "未知文档",
                "locator": f"片段 {chunk.chunk_index + 1}",
                "score": round(score, 4),
                "coverage": round(coverage, 2),
                "content": chunk.content,
            }
        )
    return results


def format_context(sources: list) -> str:
    """把检索结果拼成带编号的参考资料，模型据此标注引用。"""
    blocks = []
    for index, source in enumerate(sources, start=1):
        blocks.append(f"[{index}] {source['title']} · {source['locator']}\n{source['content']}")
    return "\n\n".join(blocks)


def public_sources(sources: list) -> list:
    """给前端展示的引用信息，正文只保留必要长度。"""
    payload = []
    for index, source in enumerate(sources, start=1):
        payload.append(
            {
                "index":    index,
                "title":    source["title"],
                "locator":  source["locator"],
                "score":    source["score"],
                "coverage": source.get("coverage", 0.0),
                "excerpt":  source["content"][:160],
            }
        )
    return payload
