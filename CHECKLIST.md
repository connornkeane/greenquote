# GreenQuote: minimum technical requirements checklist

## Presentation Tier (Client Side)
- [x] HTML pages built with Flask/Jinja templates, using a shared base layout. `templates/base.html` is extended by the dashboard, quote form, quote detail, print, and error pages.
- [x] Custom CSS styling with a consistent color scheme and typography. `static/css/style.css` uses a custom green/amber palette, a serif display font with a sans-serif body font, and no framework.
- [x] JavaScript used in a meaningful way. `static/js/quote_form.js` validates the form in the browser before submit and shows a live price estimate. `static/js/quote_detail.js` runs the forecast and AI proposal buttons.
- [x] Usable on both a computer and a phone screen. Responsive breakpoints at 900px and 600px.

## Application Tier (Server Side)
- [x] Flask application with at least three routes, at least one accepting POST. 11 routes. POST routes: `/quotes/new`, `/quotes/<id>/edit`, `/quotes/<id>/status`, `/api/estimate`, `/api/quotes/<id>/forecast`, `/api/quotes/<id>/proposal`.
- [x] Business logic written in Python. `pricing.py` (labor, materials, markup, terrain, discounts, travel tiers, tax, minimum, deposit, crew days), `services/weather.py` (work-day ratings and start-date recommendation), and the dashboard pipeline/win-rate stats in `db.py`.
- [x] Input validation and error handling. `validation.py` plus friendly 400/404/405/413/500 pages and JSON error messages.

## Data Tier
- [x] Data saved and loaded between sessions using SQLite (`data/greenquote.db`, tables `quotes`, `quote_items`, `activity`). The app creates, reads, and updates records.

## Configuration and Security
- [x] All secrets loaded from environment variables (`config.py`).
- [x] `.env` used locally, listed in `.gitignore`, never committed.
- [x] `.env.example` with placeholder values.
- [x] No calls to external services from JavaScript. All go through Flask, and the CSP `connect-src 'self'` header enforces it.

## Integration
- [x] AI API (gpt-5.4-nano) used to write customer proposals from the saved quote.
- [x] Third-party non-AI API: Open-Meteo geocoding and 7-day forecast.
- [x] File export: CSV for one quote or the whole pipeline, plus a printable / save-as-PDF estimate.

## GitHub Repository and Documentation
- [x] Code is in a new repository created for this project: https://github.com/connornkeane/greenquote
- [x] Repository is public.
- [x] README.md explains what the app does, how to install and run it, and which environment variables it needs.

## Bonus
- [x] Database (+5): SQLite with create, read, and update.
- [x] Third-party API other than AI (+5): Open-Meteo weather.
