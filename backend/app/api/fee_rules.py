from flask import Blueprint, request, jsonify
from app import db
from app.models import FeeRule
from app.utils.auth import permission_required, token_required

fee_bp = Blueprint('fee_rules', __name__)


@fee_bp.route('/', methods=['GET'])
@token_required
def list_rules(current_user):
    rules = FeeRule.query.order_by(FeeRule.id.asc()).all()
    return jsonify({'code': 200, 'data': [r.to_dict() for r in rules]})


@fee_bp.route('/', methods=['POST'])
@permission_required('fee:manage')
def create_rule(current_user):
    data = request.get_json()
    rule = FeeRule(
        rule_name      = data.get('rule_name'),
        vehicle_type   = data.get('vehicle_type', 'all'),
        fee_type       = data.get('fee_type', 'hourly'),
        free_minutes   = data.get('free_minutes', 15),
        price_per_hour = data.get('price_per_hour'),
        flat_price     = data.get('flat_price'),
        max_daily      = data.get('max_daily'),
        is_active      = data.get('is_active', 1),
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '创建成功', 'data': rule.to_dict()})


@fee_bp.route('/<int:rule_id>', methods=['PUT'])
@permission_required('fee:manage')
def update_rule(current_user, rule_id):
    rule = db.get_or_404(FeeRule, rule_id)
    data = request.get_json()
    for field in ['rule_name', 'vehicle_type', 'fee_type', 'free_minutes',
                  'price_per_hour', 'flat_price', 'max_daily', 'is_active']:
        if field in data:
            setattr(rule, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'msg': '更新成功', 'data': rule.to_dict()})


@fee_bp.route('/<int:rule_id>', methods=['DELETE'])
@permission_required('fee:manage')
def delete_rule(current_user, rule_id):
    rule = db.get_or_404(FeeRule, rule_id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '删除成功'})
