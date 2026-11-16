from services.weather import WeatherError


def create(client, csrf, form):
    form = dict(form, csrf_token=csrf)
    return client.post("/quotes/new", data=form)


def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"<h1>Quotes</h1>" in response.data


def test_security_headers(client):
    response = client.get("/")
    assert "connect-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Frame-Options"] == "DENY"


def test_create_read_update_flow(client, csrf, valid_form):
    response = create(client, csrf, valid_form)
    assert response.status_code == 302
    detail = client.get(response.headers["Location"])
    assert b"Dana Whitfield" in detail.data
    assert b"Mulch install" in detail.data

    valid_form.update(csrf_token=csrf, qty_mulch="0", qty_hedge="100")
    edited = client.post("/quotes/1/edit", data=valid_form)
    assert edited.status_code == 302
    detail = client.get("/quotes/1")
    assert b"Hedge trimming" in detail.data
    assert b"Mulch install" not in detail.data
    assert b"Re-priced at" in detail.data


def test_bad_input_shows_errors_not_crash(client, csrf):
    response = client.post("/quotes/new", data={"csrf_token": csrf, "customer_name": "", "qty_mowing": "lots"})
    assert response.status_code == 400
    assert b"Please fix the highlighted fields" in response.data


def test_post_without_csrf_is_blocked(client, valid_form):
    response = client.post("/quotes/new", data=valid_form)
    assert response.status_code == 302
    assert b"Dana Whitfield" not in client.get("/").data


def test_status_update_and_whitelist(client, csrf, valid_form):
    create(client, csrf, valid_form)
    client.post("/quotes/1/status", data={"csrf_token": csrf, "status": "Accepted"})
    assert b"status-accepted" in client.get("/quotes/1").data
    client.post("/quotes/1/status", data={"csrf_token": csrf, "status": "Paid"})
    assert b"status-accepted" in client.get("/quotes/1").data


def test_estimate_api(client, csrf):
    response = client.post(
        "/api/estimate",
        json={"terrain": "flat", "frequency": "one_time", "state": "AL", "qty_mowing": "20"},
        headers={"X-CSRFToken": csrf},
    )
    assert response.status_code == 200
    assert response.get_json()["total"] == 275.0


def test_estimate_api_rejects_bad_numbers(client, csrf):
    response = client.post(
        "/api/estimate",
        json={"terrain": "flat", "frequency": "one_time", "state": "AL", "qty_mowing": "-5"},
        headers={"X-CSRFToken": csrf},
    )
    assert response.status_code == 422


def test_proposal_without_key_is_friendly(client, csrf, valid_form):
    create(client, csrf, valid_form)
    response = client.post("/api/quotes/1/proposal", headers={"X-CSRFToken": csrf})
    assert response.status_code == 502
    assert "OPENAI_API_KEY" in response.get_json()["error"]


def test_proposal_saved_when_service_succeeds(client, csrf, valid_form, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "write_proposal", lambda *args: "Hi Dana, here is your quote.")
    create(client, csrf, valid_form)
    response = client.post("/api/quotes/1/proposal", headers={"X-CSRFToken": csrf})
    assert response.get_json()["proposal"].startswith("Hi Dana")
    assert b"Hi Dana, here is your quote." in client.get("/quotes/1").data


def test_forecast_saved_and_errors_handled(client, csrf, valid_form, monkeypatch):
    import app as app_module

    forecast = {
        "location": "Auburn, AL",
        "recommended_date": "2099-01-06",
        "days": [{"date": "2099-01-06", "weekday": "Tue", "summary": "Clear", "high_f": 70,
                  "low_f": 50, "rain_chance": 0, "wind_mph": 4, "code": 0, "rating": "Good"}],
    }
    monkeypatch.setattr(app_module, "crew_forecast", lambda *args: forecast)
    create(client, csrf, valid_form)
    response = client.post("/api/quotes/1/forecast", headers={"X-CSRFToken": csrf})
    assert response.status_code == 200
    assert b"day-pick" in client.get("/quotes/1").data

    def broken(*args):
        raise WeatherError("The weather service is unavailable right now. Try again later.")

    monkeypatch.setattr(app_module, "crew_forecast", broken)
    response = client.post("/api/quotes/1/forecast", headers={"X-CSRFToken": csrf})
    assert response.status_code == 502
    assert "unavailable" in response.get_json()["error"]


def test_exports_and_print(client, csrf, valid_form):
    create(client, csrf, valid_form)
    assert client.get("/quotes/1/export.csv").mimetype == "text/csv"
    assert b"Dana Whitfield" in client.get("/export.csv").data
    assert b"Estimate total" in client.get("/quotes/1/print").data


def test_missing_quote_is_404(client, csrf):
    assert client.get("/quotes/999").status_code == 404
    response = client.post("/api/quotes/999/proposal", headers={"X-CSRFToken": csrf})
    assert response.status_code == 404
    assert "error" in response.get_json()
