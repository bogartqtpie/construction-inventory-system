import requests

API_KEY = "PUT_YOUR_API_KEY_HERE"


def get_weather_forecast():
    url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q=Quezon City&days=7"

    try:
        res = requests.get(url)

        if res.status_code != 200:
            return []

        data = res.json()
        forecast_days = data['forecast']['forecastday']

        result = []

        for day in forecast_days:
            condition = day['day']['condition']['text'].lower()
            temp = day['day']['avgtemp_c']

            rain = 1 if "rain" in condition else 0

            result.append({
                "date": day['date'],
                "rain": rain,
                "temp": temp
            })

        return result

    except Exception as e:
        print("Weather API error:", e)
        return []
