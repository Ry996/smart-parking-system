"""
计费服务：根据停车时长计算费用
"""
from app.models import FeeRule
import math


def calculate_fee(duration_minutes: int) -> float:
    """
    :param duration_minutes: 停车时长（分钟）
    :return: 应付费用（元）
    """
    rule = FeeRule.query.filter_by(is_active=1).first()

    if not rule:
        # 默认计费：15分钟内免费，之后5元/小时
        if duration_minutes <= 15:
            return 0.0
        billable = duration_minutes - 15
        return round(math.ceil(billable / 60) * 5.0, 2)

    # 免费时长
    if duration_minutes <= rule.free_minutes:
        return 0.0

    billable = duration_minutes - rule.free_minutes

    if rule.fee_type == 'flat':
        fee = float(rule.flat_price or 0)
    else:
        # hourly：不足1小时按1小时计
        hours = math.ceil(billable / 60)
        fee = hours * float(rule.price_per_hour or 5)

    # 封顶
    if rule.max_daily and fee > float(rule.max_daily):
        fee = float(rule.max_daily)

    return round(fee, 2)
