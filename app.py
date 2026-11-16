import csv
import io
import json
import logging
import os
import secrets
from logging.handlers import RotatingFileHandler
from datetime import datetime

from flask import (
    Flask, Response, abort, flash, jsonify, redirect, render_template, request,
    session, url_for,
)

import db
from config import BASE_DIR, Config, check_config
from pricing import FREQUENCY, SERVICES, TERRAIN, calculate_quote, to_json_ready
from services.proposals import ProposalError, write_proposal
from services.weather import WeatherError, crew_forecast
from validation import STATUSES, US_STATES, validate_quote, validate_status

app = Flask(__name__)
app.config.from_object(Config)
check_config(app.config)
app.teardown_appcontext(db.close_db)

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
log_handler = RotatingFileHandler(
    os.path.join(BASE_DIR, "logs", "greenquote.log"), maxBytes=200_000, backupCount=3
)
log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)

with app.app_context():
    db.init_db()


def wants_json():
    return request.path.startswith("/api/") or request.is_json


@app.before_request
def protect_from_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    if request.method == "POST":
        sent = request.headers.get("X-CSRFToken") or request.form.get("csrf_token", "")
        if not secrets.compare_digest(sent, session["csrf_token"]):
            if wants_json():
                return jsonify(error="Your session expired. Refresh the page and try again."), 400
            app.logger.warning("Blocked POST without valid CSRF token: %s", request.path)
            flash("Your session expired. Please try again.", "error")
            return redirect(url_for("dashboard"))


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    return response


@app.context_processor
def template_globals():
    return {
        "csrf_token": session.get("csrf_token", ""),
        "business_name": app.config["BUSINESS_NAME"],
    }


@app.template_filter("money")
def money_filter(value):
    return f"${value or 0:,.2f}"


@app.template_filter("nice_date")
def nice_date_filter(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%a, %b %-d")
    except ValueError:
        return value


def form_context(values, errors, quantities, action, title):
    return {
        "values": values,
        "errors": errors,
        "quantities": quantities,
        "services": SERVICES,
        "terrain_options": TERRAIN,
        "frequency_options": FREQUENCY,
        "states": US_STATES,
        "action": action,
        "title": title,
    }


def load_quote_or_404(quote_id):
    quote, items = db.get_quote(quote_id)
    if quote is None:
        abort(404)
    return quote, items


@app.route("/")
def dashboard():
    status = request.args.get("status")
    if status and status not in STATUSES:
        status = None
    return render_template(
        "dashboard.html",
        quotes=db.list_quotes(status),
        stats=db.dashboard_stats(),
        statuses=STATUSES,
        active_status=status,
    )


@app.route("/quotes/new", methods=["GET", "POST"])
def new_quote():
    if request.method == "POST":
        clean, errors = validate_quote(request.form)
        if not errors:
            result = calculate_quote(
                clean["quantities"], clean["terrain"], clean["frequency"], clean["travel_miles"]
            )
            quote_id = db.create_quote(clean, result)
            flash("Quote saved. Check the crew forecast, then generate the proposal.", "success")
            return redirect(url_for("quote_detail", quote_id=quote_id))
        flash("Please fix the highlighted fields.", "error")
        return render_template(
            "quote_form.html",
            **form_context(request.form, errors, clean["quantities"], url_for("new_quote"), "New quote"),
        ), 400
    defaults = {"terrain": "flat", "frequency": "one_time", "state": "AL", "travel_miles": "0"}
    return render_template(
        "quote_form.html", **form_context(defaults, {}, {}, url_for("new_quote"), "New quote")
    )


@app.route("/quotes/<int:quote_id>")
def quote_detail(quote_id):
    quote, items = load_quote_or_404(quote_id)
    forecast = json.loads(quote["forecast_json"]) if quote["forecast_json"] else None
    return render_template(
        "quote_detail.html",
        quote=quote,
        items=items,
        forecast=forecast,
        activity=db.get_activity(quote_id),
        statuses=STATUSES,
        terrain_label=TERRAIN[quote["terrain"]]["label"],
        frequency_label=FREQUENCY[quote["frequency"]]["label"],
    )


@app.route("/quotes/<int:quote_id>/edit", methods=["GET", "POST"])
def edit_quote(quote_id):
    quote, items = load_quote_or_404(quote_id)
    action = url_for("edit_quote", quote_id=quote_id)
    if request.method == "POST":
        clean, errors = validate_quote(request.form)
        if not errors:
            result = calculate_quote(
                clean["quantities"], clean["terrain"], clean["frequency"], clean["travel_miles"]
            )
            db.update_quote(quote_id, clean, result)
            flash("Quote updated. Regenerate the proposal so it matches the new price.", "success")
            return redirect(url_for("quote_detail", quote_id=quote_id))
        flash("Please fix the highlighted fields.", "error")
        return render_template(
            "quote_form.html",
            **form_context(request.form, errors, clean["quantities"], action, f"Edit quote #{quote_id}"),
        ), 400
    return render_template(
        "quote_form.html",
        **form_context(dict(quote), {}, db.quote_quantities(items), action, f"Edit quote #{quote_id}"),
    )


@app.route("/quotes/<int:quote_id>/status", methods=["POST"])
def change_status(quote_id):
    load_quote_or_404(quote_id)
    status = validate_status(request.form.get("status", ""))
    if status is None:
        flash("That status isn't allowed.", "error")
    else:
        db.update_status(quote_id, status)
        flash(f"Quote marked {status}.", "success")
    return redirect(url_for("quote_detail", quote_id=quote_id))


@app.route("/api/estimate", methods=["POST"])
def api_estimate():
    data = request.get_json(silent=True) or {}
    clean, errors = validate_quote(data)
    errors.pop("customer_name", None)
    errors.pop("customer_email", None)
    errors.pop("city", None)
    if errors:
        return jsonify(errors=errors), 422
    result = calculate_quote(
        clean["quantities"], clean["terrain"], clean["frequency"], clean["travel_miles"]
    )
    return jsonify(to_json_ready(result))


@app.route("/api/quotes/<int:quote_id>/forecast", methods=["POST"])
def api_forecast(quote_id):
    quote, _items = load_quote_or_404(quote_id)
    try:
        forecast = crew_forecast(
            quote["city"], quote["state"], app.config["GEOCODE_URL"], app.config["FORECAST_URL"]
        )
    except WeatherError as exc:
        app.logger.warning("Forecast failed for quote %s: %r", quote_id, exc.__cause__ or exc)
        return jsonify(error=str(exc)), 502
    db.save_forecast(quote_id, forecast)
    return jsonify(forecast)


@app.route("/api/quotes/<int:quote_id>/proposal", methods=["POST"])
def api_proposal(quote_id):
    quote, items = load_quote_or_404(quote_id)
    try:
        proposal = write_proposal(
            quote, items, app.config["OPENAI_API_KEY"], app.config["OPENAI_MODEL"],
            app.config["BUSINESS_NAME"],
        )
    except ProposalError as exc:
        app.logger.warning("Proposal failed for quote %s: %r", quote_id, exc.__cause__ or exc)
        return jsonify(error=str(exc)), 502
    db.save_proposal(quote_id, proposal)
    return jsonify(proposal=proposal)


@app.route("/quotes/<int:quote_id>/print")
def print_quote(quote_id):
    quote, items = load_quote_or_404(quote_id)
    return render_template(
        "quote_print.html",
        quote=quote,
        items=items,
        terrain_label=TERRAIN[quote["terrain"]]["label"],
        frequency_label=FREQUENCY[quote["frequency"]]["label"],
        printed_on=datetime.now().strftime("%B %-d, %Y"),
    )


@app.route("/quotes/<int:quote_id>/export.csv")
def export_quote(quote_id):
    quote, items = load_quote_or_404(quote_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Quote", quote_id, "Customer", quote["customer_name"], "Status", quote["status"]])
    writer.writerow([])
    writer.writerow(["Service", "Quantity", "Unit", "Labor", "Materials", "Line total"])
    for item in items:
        writer.writerow([
            item["label"], item["quantity"], item["unit"],
            f"{item['labor_cost']:.2f}", f"{item['material_cost']:.2f}", f"{item['line_total']:.2f}",
        ])
    writer.writerow([])
    for label, key in [
        ("Recurring discount", "discount"), ("Travel fee", "travel_fee"),
        ("Minimum job adjustment", "minimum_adjustment"), ("Subtotal", "subtotal"),
        ("Sales tax", "tax"), ("Total", "total"), ("Deposit due", "deposit"),
    ]:
        writer.writerow([label, "", "", "", "", f"{quote[key]:.2f}"])
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=greenquote-{quote_id}.csv"},
    )


@app.route("/export.csv")
def export_all():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "customer", "email", "city", "state", "status", "total", "deposit",
                     "crew_days", "recommended_date", "updated_at"])
    for quote in db.list_quotes():
        writer.writerow([
            quote["id"], quote["customer_name"], quote["customer_email"], quote["city"],
            quote["state"], quote["status"], f"{quote['total']:.2f}", f"{quote['deposit']:.2f}",
            quote["crew_days"], quote["recommended_date"] or "", quote["updated_at"],
        ])
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=greenquote-pipeline.csv"},
    )


@app.errorhandler(404)
def not_found(_error):
    if wants_json():
        return jsonify(error="That quote doesn't exist."), 404
    return render_template("error.html", code=404, message="We couldn't find that page or quote."), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    if wants_json():
        return jsonify(error="That action isn't allowed here."), 405
    return render_template("error.html", code=405, message="That action isn't allowed here."), 405


@app.errorhandler(413)
def too_large(_error):
    if wants_json():
        return jsonify(error="That request was too large."), 413
    return render_template("error.html", code=413, message="That form was too large to process."), 413


@app.errorhandler(500)
def server_error(_error):
    app.logger.error("Unhandled error on %s %s", request.method, request.path)
    if wants_json():
        return jsonify(error="Something went wrong on our side. Try again."), 500
    return render_template(
        "error.html", code=500, message="Something went wrong on our side. Your data is safe; try again."
    ), 500


@app.cli.command("seed-demo")
def seed_demo():
    samples = [
        ({"customer_name": "Dana Whitfield", "customer_email": "dana.whitfield@example.com",
          "customer_phone": "3345550142", "city": "Auburn", "state": "AL", "travel_miles": 6,
          "terrain": "flat", "frequency": "weekly", "notes": "Gate code at the side yard."},
         {"mowing": 12, "hedge": 140}, "Accepted"),
        ({"customer_name": "Marcus Lee", "customer_email": "marcus.lee@example.com",
          "customer_phone": "", "city": "Opelika", "state": "AL", "travel_miles": 14,
          "terrain": "moderate", "frequency": "one_time", "notes": "Wants beds refreshed before a party."},
         {"cleanup": 8, "mulch": 9, "hedge": 220}, "Sent"),
        ({"customer_name": "Grace Okafor", "customer_email": "grace.okafor@example.com",
          "customer_phone": "3345550199", "city": "Auburn", "state": "AL", "travel_miles": 4,
          "terrain": "steep", "frequency": "one_time", "notes": "Backyard slope, two dead zones."},
         {"sod": 1800, "irrigation": 2}, "Declined"),
    ]
    for clean, quantities, status in samples:
        clean["quantities"] = quantities
        result = calculate_quote(quantities, clean["terrain"], clean["frequency"], clean["travel_miles"])
        quote_id = db.create_quote(clean, result)
        db.update_status(quote_id, status)
    print(f"Added {len(samples)} demo quotes.")


if __name__ == "__main__":
    app.run(debug=False)
