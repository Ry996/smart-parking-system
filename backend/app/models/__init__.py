from app import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(50), nullable=False, unique=True)
    password   = db.Column(db.String(255), nullable=False)
    real_name  = db.Column(db.String(50))
    role       = db.Column(db.Enum('admin', 'operator'), nullable=False, default='operator')
    status     = db.Column(db.SmallInteger, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':        self.id,
            'username':  self.username,
            'real_name': self.real_name,
            'role':      self.role,
            'status':    self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }


class ParkingRecord(db.Model):
    __tablename__ = 'parking_records'

    id           = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    plate_number = db.Column(db.String(20), nullable=False, index=True)
    plate_type   = db.Column(db.String(20), default='blue')
    entry_time   = db.Column(db.DateTime, nullable=False)
    exit_time    = db.Column(db.DateTime)
    duration     = db.Column(db.Integer)            # 分钟
    fee          = db.Column(db.Numeric(10, 2))
    status       = db.Column(db.Enum('parked', 'exited', 'exception'), default='parked')
    payment_status = db.Column(db.String(10), default='unpaid', index=True)  # unpaid待支付/paid已支付/free免费放行
    payment_time   = db.Column(db.DateTime)
    entry_image  = db.Column(db.String(255))
    exit_image   = db.Column(db.String(255))
    operator_id  = db.Column(db.Integer)
    remark       = db.Column(db.String(255))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':             self.id,
            'plate_number':   self.plate_number,
            'plate_type':     self.plate_type,
            'entry_time':     self.entry_time.strftime('%Y-%m-%d %H:%M:%S') if self.entry_time else None,
            'exit_time':      self.exit_time.strftime('%Y-%m-%d %H:%M:%S') if self.exit_time else None,
            'duration':       self.duration,
            'fee':            float(self.fee) if self.fee is not None else None,
            'status':         self.status,
            'payment_status': self.payment_status,
            'payment_time':   self.payment_time.strftime('%Y-%m-%d %H:%M:%S') if self.payment_time else None,
            'entry_image':    self.entry_image,
            'exit_image':     self.exit_image,
            'operator_id':    self.operator_id,
            'remark':         self.remark,
        }


class FeeRule(db.Model):
    __tablename__ = 'fee_rules'

    id             = db.Column(db.Integer, primary_key=True)
    rule_name      = db.Column(db.String(100), nullable=False)
    vehicle_type   = db.Column(db.String(20), default='all')
    fee_type       = db.Column(db.Enum('hourly', 'flat'), default='hourly')
    free_minutes   = db.Column(db.Integer, default=15)
    price_per_hour = db.Column(db.Numeric(10, 2))
    flat_price     = db.Column(db.Numeric(10, 2))
    max_daily      = db.Column(db.Numeric(10, 2))
    time_start     = db.Column(db.Time)
    time_end       = db.Column(db.Time)
    is_active      = db.Column(db.SmallInteger, default=1)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':             self.id,
            'rule_name':      self.rule_name,
            'vehicle_type':   self.vehicle_type,
            'fee_type':       self.fee_type,
            'free_minutes':   self.free_minutes,
            'price_per_hour': float(self.price_per_hour) if self.price_per_hour is not None else None,
            'flat_price':     float(self.flat_price) if self.flat_price is not None else None,
            'max_daily':      float(self.max_daily) if self.max_daily is not None else None,
            'time_start':     str(self.time_start) if self.time_start else None,
            'time_end':       str(self.time_end) if self.time_end else None,
            'is_active':      self.is_active,
        }


class ParkingSpace(db.Model):
    __tablename__ = 'parking_spaces'

    id        = db.Column(db.Integer, primary_key=True)
    total     = db.Column(db.Integer, default=100)
    available = db.Column(db.Integer, default=100)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonthlySubscriber(db.Model):
    """月租车辆表：按月租赁车位的车辆，离场按套餐计费（通常 0 元放行）。"""
    __tablename__ = 'monthly_subscribers'

    id           = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False, unique=True, index=True)
    owner_name   = db.Column(db.String(50), nullable=False)
    phone        = db.Column(db.String(20))
    package_name = db.Column(db.String(100), nullable=False)
    start_date   = db.Column(db.Date, nullable=False)
    end_date     = db.Column(db.Date, nullable=False)
    fee          = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    remark       = db.Column(db.String(255))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def _status(self):
        """动态计算订阅状态：expired-已过期 / soon-即将到期(7天内) / active-生效中"""
        today = datetime.utcnow().date()
        if self.end_date < today:
            return "expired"
        if (self.end_date - today).days <= 7:
            return "soon"
        return "active"

    def to_dict(self):
        return {
            'id':           self.id,
            'plate_number': self.plate_number,
            'owner_name':   self.owner_name,
            'phone':        self.phone,
            'package_name': self.package_name,
            'start_date':   self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date':     self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'fee':          float(self.fee) if self.fee is not None else 0,
            'status':       self._status(),
            'remark':       self.remark,
        }


class ParkingReservation(db.Model):
    """车位预约表：车主提前预约入场时段，入场时优先放行。"""
    __tablename__ = 'parking_reservations'

    id           = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False, index=True)
    owner_name   = db.Column(db.String(50))
    phone        = db.Column(db.String(20))
    start_time   = db.Column(db.DateTime, nullable=False)
    end_time     = db.Column(db.DateTime, nullable=False)
    status       = db.Column(db.Enum('pending', 'arrived', 'cancelled', 'expired'), default='pending')
    remark       = db.Column(db.String(255))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'plate_number': self.plate_number,
            'owner_name':   self.owner_name,
            'phone':        self.phone,
            'start_time':   self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time':     self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'status':       self.status,
            'remark':       self.remark,
        }


class Blacklist(db.Model):
    """黑名单表：欠费、逃费、恶意占位等车辆，入场时拦截。"""
    __tablename__ = 'blacklist'

    id           = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False, unique=True, index=True)
    reason       = db.Column(db.String(255))
    debt_amount  = db.Column(db.Numeric(10, 2), default=0)
    is_active    = db.Column(db.SmallInteger, nullable=False, default=1)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'plate_number': self.plate_number,
            'reason':       self.reason,
            'debt_amount':  float(self.debt_amount) if self.debt_amount is not None else 0,
            'is_active':    self.is_active,
            'created_at':   self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }


class OperationLog(db.Model):
    """操作日志表：记录登录、入离场、配置变更等关键操作的审计日志。"""
    __tablename__ = 'operation_logs'

    id         = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer)
    username   = db.Column(db.String(50))
    action     = db.Column(db.String(50), nullable=False, index=True)
    target     = db.Column(db.String(100))
    detail     = db.Column(db.String(255))
    ip         = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id':         self.id,
            'user_id':    self.user_id,
            'username':   self.username,
            'action':     self.action,
            'target':     self.target,
            'detail':     self.detail,
            'ip':         self.ip,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 实验四：RBAC 角色权限模型
# users.role 仍保存角色编码（admin / operator），与 roles.code 对应，
# 这样历史数据与既有接口字段完全兼容，同时补齐"用户-角色-权限"三张表。
# ---------------------------------------------------------------------------


class Role(db.Model):
    __tablename__ = 'roles'

    id          = db.Column(db.Integer, primary_key=True)
    code        = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name        = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    is_builtin  = db.Column(db.SmallInteger, nullable=False, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, permissions=None):
        data = {
            'id':          self.id,
            'code':        self.code,
            'name':        self.name,
            'description': self.description,
            'is_builtin':  self.is_builtin,
        }
        if permissions is not None:
            data['permissions'] = list(permissions)
        return data


class Permission(db.Model):
    __tablename__ = 'permissions'

    id          = db.Column(db.Integer, primary_key=True)
    code        = db.Column(db.String(60), nullable=False, unique=True, index=True)
    name        = db.Column(db.String(60), nullable=False)
    group_name  = db.Column(db.String(30), nullable=False, default='其他')
    description = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id':          self.id,
            'code':        self.code,
            'name':        self.name,
            'group_name':  self.group_name,
            'description': self.description,
        }


class RolePermission(db.Model):
    __tablename__ = 'role_permissions'

    role_id       = db.Column(db.Integer, primary_key=True)
    permission_id = db.Column(db.Integer, primary_key=True)


# ---------------------------------------------------------------------------
# 实验五：AI 调用留痕、幻觉案例反馈、RAG 知识库
# ---------------------------------------------------------------------------


class AiCall(db.Model):
    """每次大模型调用的可审计记录：输入脱敏、输出截断，便于报告取证。"""
    __tablename__ = 'ai_calls'

    id             = db.Column(db.Integer, primary_key=True)
    purpose        = db.Column(db.String(40), nullable=False, index=True)
    provider       = db.Column(db.String(30), default='deepseek')
    model          = db.Column(db.String(60))
    prompt_version = db.Column(db.String(30))
    input_summary  = db.Column(db.String(1000))
    raw_output     = db.Column(db.Text)
    final_output   = db.Column(db.Text)
    duration_ms    = db.Column(db.Integer)
    error_message  = db.Column(db.String(500))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id':             self.id,
            'purpose':        self.purpose,
            'provider':       self.provider,
            'model':          self.model,
            'prompt_version': self.prompt_version,
            'input_summary':  self.input_summary,
            'final_output':   self.final_output,
            'duration_ms':    self.duration_ms,
            'error_message':  self.error_message,
            'created_at':     self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }


class AiFeedback(db.Model):
    """AI 输出的人工复核记录：沉淀幻觉 / 引用错误 / 提示注入等真实案例。"""
    __tablename__ = 'ai_feedback'

    id              = db.Column(db.Integer, primary_key=True)
    question        = db.Column(db.Text, nullable=False)
    answer          = db.Column(db.Text)
    category        = db.Column(db.String(30), nullable=False, index=True)
    expected_answer = db.Column(db.Text)
    note            = db.Column(db.String(500))
    mode            = db.Column(db.String(20))
    reporter        = db.Column(db.String(50))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id':              self.id,
            'question':        self.question,
            'answer':          self.answer,
            'category':        self.category,
            'expected_answer': self.expected_answer,
            'note':            self.note,
            'mode':            self.mode,
            'reporter':        self.reporter,
            'created_at':      self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }


class KnowledgeDocument(db.Model):
    """RAG 知识库文档：停车场计费、出入场、月租预约等业务规则的权威文本。"""
    __tablename__ = 'knowledge_documents'

    id          = db.Column(db.Integer, primary_key=True)
    code        = db.Column(db.String(60), nullable=False, unique=True, index=True)
    title       = db.Column(db.String(120), nullable=False)
    category    = db.Column(db.String(40), default='业务规则')
    content     = db.Column(db.Text, nullable=False)
    chunk_count = db.Column(db.Integer, default=0)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, with_content=False):
        data = {
            'id':          self.id,
            'code':        self.code,
            'title':       self.title,
            'category':    self.category,
            'chunk_count': self.chunk_count,
            'updated_at':  self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
        if with_content:
            data['content'] = self.content
        return data


class KnowledgeChunk(db.Model):
    """知识库切块及其向量（哈希向量，避免依赖外部 embedding 服务）。"""
    __tablename__ = 'knowledge_chunks'

    id          = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    content     = db.Column(db.Text, nullable=False)
    embedding   = db.Column(db.Text)

    def to_dict(self):
        return {
            'id':          self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'content':     self.content,
        }
