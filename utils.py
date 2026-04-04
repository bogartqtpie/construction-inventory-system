# utils.py
from datetime import datetime
from models import Material, UsageLog
import numpy as np


def get_low_stock(exclude_ids=None):
    """
    Returns materials that are below or equal to their reorder point.
    Adds temporary 'qty' attribute for template use.

    exclude_ids: list of material IDs to filter out (e.g., dismissed notifications).
    """
    query = Material.query.filter(Material.quantity <= Material.reorder_point)
    if exclude_ids:
        query = query.filter(~Material.id.in_(exclude_ids))
    low_materials = query.all()
    for m in low_materials:
        m.qty = m.quantity
        if not hasattr(m, 'pred_days'):
            m.pred_days = None
    return low_materials


def predict_depletion_days(material):
    """
    Predicts how many days before a material runs out using Linear Regression.
    Uses UsageLog data (date vs cumulative used quantity).
    Returns:
        float: Estimated days until depletion
        None: If not enough data or stock not decreasing
    """

    try:
        # Get usage logs for this material (oldest first)
        usage_logs = UsageLog.query.filter_by(
            material_id=material.id).order_by(UsageLog.date).all()

        # Need at least 3 data points for meaningful regression
        if len(usage_logs) < 3:
            return None

        # Build cumulative used quantity over time
        cumulative_used = []
        total_used = 0
        for log in usage_logs:
            total_used += log.used_quantity
            cumulative_used.append(total_used)

        dates = np.array([
            (log.date - usage_logs[0].date).days
            for log in usage_logs
        ]).reshape(-1, 1)

        quantities = np.array([
            material.quantity - used for used in cumulative_used
        ])

        # If stock not decreasing
        if np.all(quantities == quantities[0]):
            return None

        # Linear regression
        # Convert to 1D lists
        x_values = [d[0] for d in dates]
        y_values = list(quantities)

        n = len(x_values)
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum((x - x_mean) * (y - y_mean)
                        for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        # Avoid division by zero
        if denominator == 0:
            return None

        m = numerator / denominator
        b = y_mean - (m * x_mean)

        # If slope >= 0 → stock increasing, no depletion
        if m >= 0:
            return None

        # Predict day stock reaches zero: 0 = m*x + b → x = -b/m
        days_until_empty = -b / m
        current_day = dates[-1][0]
        days_remaining = days_until_empty - current_day

        if days_remaining <= 0:
            return 0

        return round(days_remaining, 1)

    except Exception as e:
        print(
            f"⚠️ Error in predict_depletion_days for material '{material.name}': {e}")
        return None
