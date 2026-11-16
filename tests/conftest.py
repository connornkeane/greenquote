import os
import sys
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")
os.environ.setdefault("OPENAI_API_KEY", "")


@pytest.fixture
def app(tmp_path):
    from app import app as flask_app
    import db

    flask_app.config.update(TESTING=True, DATABASE_PATH=str(tmp_path / "test.db"), OPENAI_API_KEY="")
    with flask_app.app_context():
        db.init_db()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf(client):
    page = client.get("/")
    return re.search(r'name="csrf-token" content="([^"]+)"', page.get_data(as_text=True)).group(1)


@pytest.fixture
def valid_form():
    return {
        "customer_name": "Dana Whitfield",
        "customer_email": "dana@example.com",
        "customer_phone": "(334) 555-0142",
        "city": "Auburn",
        "state": "AL",
        "travel_miles": "12",
        "terrain": "moderate",
        "frequency": "weekly",
        "notes": "Side gate",
        "qty_mowing": "10",
        "qty_mulch": "4",
    }
