from datetime import datetime, timedelta
from models import Material  # assuming you have a models.py file

# Function to get low-stock materials
def get_low_stock():
    """
    Returns a list of materials that are below or equal to their reorder point.
    """
    low_stock = Material.query.filter(Material.quantity <= Material.reorder_point).all()
    return low_stock

# Function to predict depletion days (optional simple logic)
def predict_depletion_days(material):
    """
    Estimates how many days before the stock runs out, based on average usage.
    For now, this is a simple placeholder — you can expand this using Linear Regression later.
    """
    # Example: assume fixed daily usage rate for simplicity
    daily_usage = 5  # you can replace this with actual computed values
    if material.quantity > 0 and daily_usage > 0:
        days_left = material.quantity / daily_usage
        return round(days_left, 1)
    else:
        return 0
