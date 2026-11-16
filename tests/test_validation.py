from validation import validate_quote, validate_status


def test_valid_form_is_clean(valid_form):
    clean, errors = validate_quote(valid_form)
    assert errors == {}
    assert clean["customer_phone"] == "3345550142"
    assert clean["customer_email"] == "dana@example.com"
    assert clean["quantities"]["mowing"] == 10


def test_requires_a_service(valid_form):
    valid_form["qty_mowing"] = ""
    valid_form["qty_mulch"] = "0"
    _clean, errors = validate_quote(valid_form)
    assert "services" in errors


def test_rejects_bad_values(valid_form):
    valid_form.update(
        customer_email="not-an-email", state="ZZ", terrain="lava", qty_mulch="-3",
        travel_miles="999", customer_phone="123", qty_sod="abc",
    )
    _clean, errors = validate_quote(valid_form)
    for key in ["customer_email", "state", "terrain", "qty_mulch", "travel_miles", "customer_phone", "qty_sod"]:
        assert key in errors


def test_rejects_nan_and_script_tags(valid_form):
    valid_form["qty_mowing"] = "nan"
    valid_form["customer_name"] = "<script>alert(1)</script>"
    _clean, errors = validate_quote(valid_form)
    assert "qty_mowing" in errors
    assert "customer_name" in errors


def test_status_whitelist():
    assert validate_status("Accepted") == "Accepted"
    assert validate_status("Paid") is None
