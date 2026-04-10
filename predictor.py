from models import Sale


def train_model():
    sales = Sale.query.all()

    if len(sales) < 3:
        return None

    # Use average sales as simple baseline
    total_sales = [s.total for s in sales]
    avg_sales = sum(total_sales) / len(total_sales)

    return {
        "avg_sales": avg_sales
    }


def predict_demand(model, weather_data):
    if model is None or not weather_data:
        return []

    predictions = []

    for day in weather_data:
        base = model["avg_sales"]

        # Simple adjustment based on rain
        if day["rain"] == 1:
            base *= 0.8   # decrease demand when rainy
        else:
            base *= 1.1   # increase demand when not rainy

        predictions.append({
            "date": day["date"],
            "prediction": round(base, 2),
            "rain": day["rain"]
        })

    return predictions
