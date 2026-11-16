from datetime import date, datetime

import requests

from validation import US_STATES

TIMEOUT_SECONDS = 8

STORM_CODES = {65, 67, 75, 82, 86, 95, 96, 99}

WEATHER_LABELS = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Showers", 81: "Showers",
    82: "Heavy showers", 85: "Snow showers", 86: "Snow showers", 95: "Thunderstorms",
    96: "Thunderstorms", 99: "Thunderstorms",
}


class WeatherError(Exception):
    pass


def _get_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise WeatherError("The weather service took too long to respond. Try again in a minute.") from exc
    except (requests.RequestException, ValueError) as exc:
        raise WeatherError("The weather service is unavailable right now. Try again later.") from exc


def geocode(city, state, url):
    data = _get_json(url, {"name": city, "count": 10, "countryCode": "US", "language": "en"})
    state_name = US_STATES.get(state, "")
    for place in data.get("results") or []:
        if place.get("admin1") == state_name:
            return place["latitude"], place["longitude"], f"{place['name']}, {state}"
    raise WeatherError(f"Couldn't find {city}, {state} on the map. Check the city spelling.")


def rate_day(day):
    rain = day["rain_chance"]
    if rain >= 60 or day["code"] in STORM_CODES or day["wind_mph"] >= 30:
        return "Poor"
    if rain >= 30 or day["wind_mph"] >= 20 or day["high_f"] >= 95 or day["low_f"] <= 32:
        return "Fair"
    return "Good"


def recommend_date(days, today=None):
    today = today or date.today()
    candidates = [
        d for d in days
        if datetime.strptime(d["date"], "%Y-%m-%d").date() > today
        and datetime.strptime(d["date"], "%Y-%m-%d").weekday() != 6
    ]
    for rating in ("Good", "Fair"):
        for day in candidates:
            if day["rating"] == rating:
                return day["date"]
    return None


def crew_forecast(city, state, geocode_url, forecast_url):
    latitude, longitude, label = geocode(city, state, geocode_url)
    data = _get_json(
        forecast_url,
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max,wind_speed_10m_max",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "auto",
            "forecast_days": 7,
        },
    )
    daily = data.get("daily")
    if not daily or not daily.get("time"):
        raise WeatherError("The weather service returned an empty forecast.")

    days = []
    for i, day_str in enumerate(daily["time"]):
        code = int(daily["weather_code"][i] or 0)
        day = {
            "date": day_str,
            "weekday": datetime.strptime(day_str, "%Y-%m-%d").strftime("%a"),
            "code": code,
            "summary": WEATHER_LABELS.get(code, "Mixed"),
            "high_f": round(daily["temperature_2m_max"][i] or 0),
            "low_f": round(daily["temperature_2m_min"][i] or 0),
            "rain_chance": int(daily["precipitation_probability_max"][i] or 0),
            "wind_mph": round(daily["wind_speed_10m_max"][i] or 0),
        }
        day["rating"] = rate_day(day)
        days.append(day)

    return {"location": label, "days": days, "recommended_date": recommend_date(days)}
