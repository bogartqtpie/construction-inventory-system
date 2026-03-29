import numpy as np
from sklearn.linear_model import LinearRegression
from models import Sale


def train_model():
    sales = Sale.query.all()

    X = []
    y = []

    for s in sales:
        # Temporary weather approximation
        rain = 1 if s.date.month in [6, 7, 8, 9] else 0
        temp = 30

        X.append([s.total, rain, temp])
        y.append(s.total)

    if len(X) < 3:
        return None

    model = LinearRegression()
    model.fit(X, y)

    return model


def predict_demand(model, weather_data):
    if model is None or not weather_data:
        return []

    predictions = []

    for day in weather_data:
        sample = np.array([[50, day["rain"], day["temp"]]])
        pred = model.predict(sample)[0]

        predictions.append({
            "date": day["date"],
            "prediction": float(pred),
            "rain": day["rain"]
        })

    return predictions
