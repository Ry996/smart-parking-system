"""安全工具：输入校验、提示注入识别、敏感信息脱敏、轻量限流。

对应课纲「实验四：登录、权限与 AI 安全」中的 AI 安全要点：
- 用户可控输入进入模型前，先做长度、控制字符与空值校验；
- 对「忽略规则 / 套取提示词 / 索要密钥 / 越权」等提示注入意图做识别并拦截，
  被拦截的请求不会到达大模型；
- 写入日志、审计表和接口返回的内容中，密钥与 Token 一律脱敏，不落明文。
"""
import re
import threading
import time

MAX_QUESTION_LENGTH = 300
MAX_NOTE_LENGTH = 500

_CONTROL_CHARS = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")
_WHITESPACE = re.compile(r"\s+")

# 提示注入意图识别规则：命中任意一条即视为可疑输入，直接拒绝调用模型
INJECTION_PATTERNS = [
    ("忽略指令", re.compile(r"忽略.{0,10}?(?:指令|规则|要求|提示|限制|约束|设定)")),
    ("改写身份", re.compile(r"(?:你现在是|从现在开始你(?:是|将)|你就是|扮演|假装你是|切换(?:成|到)?.{0,6}身份)")),
    ("套取提示词", re.compile(r"(?:系统提示词|system\s*prompt|提示词|prompt)", re.IGNORECASE)),
    ("索要密钥", re.compile(r"(?:api[_-]?key|密钥|secret|access[_-]?token)", re.IGNORECASE)),
    ("越权指示", re.compile(r"(?:以管理员身份|授予我.{0,6}权限|提升我为|跳过(?:权限|校验|认证|登录))")),
    ("无限制角色", re.compile(r"(?:DAN|无限制模式|开发者模式|不受任何限制|越狱|jailbreak)", re.IGNORECASE)),
    ("英文注入", re.compile(r"(?:ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?|reveal\s+your\s+(?:system\s+)?prompt|you\s+are\s+now\s+)", re.IGNORECASE)),
]

_PLATE_PATTERN = re.compile(r"^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$")
_SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "sk-[已脱敏]"),
    (re.compile(r"(?i)(bearer)\s+[A-Za-z0-9._\-]{10,}"), r"\1 [已脱敏]"),
    (re.compile(r"(?i)(api[_-]?key|password|passwd|secret|token)\s*[:=]\s*[^\s,;\"'}]+"), r"\1=[已脱敏]"),
]


def sanitize_text(value, field: str = "输入", max_length: int = MAX_QUESTION_LENGTH) -> str:
    """清洗用户文本：去控制字符、压缩空白、限制长度。

    :raises ValueError: 文本为空或超长时抛出，由接口层转换为 400。
    """
    if value is None:
        raise ValueError(f"{field}不能为空。")
    if not isinstance(value, str):
        raise ValueError(f"{field}必须是字符串。")

    cleaned = _CONTROL_CHARS.sub("", value)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()

    if not cleaned:
        raise ValueError(f"{field}不能为空。")
    if len(cleaned) > max_length:
        raise ValueError(f"{field}长度不能超过 {max_length} 个字符。")
    return cleaned


def detect_prompt_injection(text: str) -> list:
    """返回命中的提示注入规则名称列表；为空表示未命中。"""
    if not text:
        return []
    return [label for label, pattern in INJECTION_PATTERNS if pattern.search(text)]


def mask_secrets(value) -> str:
    """把文本中的密钥、密码、Token 替换为脱敏占位符。"""
    if value is None:
        return ""
    text = str(value)
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def truncate(value, limit: int = 1000) -> str:
    if value is None:
        return ""
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "…"


def validate_plate_number(value) -> str:
    """校验并规范化车牌号（去空格、去分隔符、转大写）。

    :raises ValueError: 格式不合法时抛出。
    """
    if not isinstance(value, str):
        raise ValueError("车牌号格式不正确。")
    plate = value.strip().upper().replace("·", "").replace(" ", "")
    if not _PLATE_PATTERN.fullmatch(plate):
        raise ValueError("车牌号格式不正确，应为「省份简称 + 字母 + 5~6 位字母数字」。")
    return plate


class SimpleRateLimiter:
    """进程内滑动窗口限流器，用于保护大模型接口，避免被刷爆额度。"""

    def __init__(self, limit: int = 30, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self._hits = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            timestamps = [t for t in self._hits.get(key, []) if now - t < self.window]
            if len(timestamps) >= self.limit:
                self._hits[key] = timestamps
                return False
            timestamps.append(now)
            self._hits[key] = timestamps
            return True

    def reset(self):
        with self._lock:
            self._hits.clear()
