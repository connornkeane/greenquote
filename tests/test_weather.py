from datetime import date

import pytest
import requests

from services import weather


def make_day(day, rain=0, code=0, high=75, low=55, wind=5):
    return {"date": day, "rain_chance": rain, "code": code, "high_f": high, "low_f": low, "wind_mph": wind}


def test_rate_day():
    assert weather.rate_day(make_day("2026-11-17")) == "Good"
    assert weather.rate_day(make_day("2026-11-17", rain=40)) == "Fair"
    assert weather.rate_day(make_day("2026-11-17", low=30)) == "Fair"
    assert weather.rate_day(make_day("2026-11-17", rain=70)) == "Poor"
    assert weather.rate_day(make_day("2026-11-17", code=95)) == "Poor"


def test_recommend_skips_today_sunday_and_bad_days():
    days = [
        make_day("2026-11-16"),
        make_day("2026-11-17", rain=80),
        make_day("2026-11-18", rain=40),
        make_day("2026-11-22"),
        make_day("2026-11-23"),
    ]
    for d in days:
        d["rating"] = weather.rate_day(d)
    assert weather.recommend_date(days, today=date(2026, 11, 16)) == "2026-11-23"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_crew_forecast_end_to_end(monkeypatch):
    def fake_get(url, params, timeout):
        if "geocode" in url:
            return FakeResponse({"results": [
                {"name": "Auburn", "admin1": "Washington", "latitude": 47.3, "longitude": -122.2},
                {"name": "Auburn", "admin1": "Alabama", "latitude": 32.6, "longitude": -85.5},
            ]})
        assert params["latitude"] == 32.6
        return FakeResponse({"daily": {
            "time": ["2099-01-05", "2099-01-06"],
            "weather_code": [61, 1],
            "temperature_2m_max": [60, 66],
            "temperature_2m_min": [44, 45],
            "precipitation_probability_max": [80, 5],
            "wind_speed_10m_max": [10, 6],
        }})

    monkeypatch.setattr(weather.requests, "get", fake_get)
    result = weather.crew_forecast("Auburn", "AL", "https://geocode", "https://forecast")
    assert result["location"] == "Auburn, AL"
    assert [d["rating"] for d in result["days"]] == ["Poor", "Good"]
    assert result["recommended_date"] == "2099-01-06"


def test_timeout_becomes_friendly_error(monkeypatch):
    def slow(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(weather.requests, "get", slow)
    with pytest.raises(weather.WeatherError, match="too long"):
        weather.crew_forecast("Auburn", "AL", "https://geocode", "https://forecast")
