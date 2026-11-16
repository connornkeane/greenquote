import re

from pricing import FREQUENCY, MAX_TRAVEL_MILES, SERVICES, TERRAIN

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .,'&-]{1,79}$")
CITY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,59}$")

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

STATUSES = ["Draft", "Sent", "Accepted", "Declined"]


def _text(data, key):
    value = data.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def _number(data, key, errors, label, minimum, maximum):
    raw = _text(data, key)
    if raw == "":
        return 0.0
    try:
        value = float(raw)
    except ValueError:
        errors[key] = f"{label} must be a number."
        return 0.0
    if value != value or value < minimum or value > maximum:
        errors[key] = f"{label} must be between {minimum:g} and {maximum:g}."
        return 0.0
    return round(value, 2)


def validate_quote(data):
    errors = {}
    clean = {}

    name = _text(data, "customer_name")
    if not NAME_PATTERN.match(name):
        errors["customer_name"] = "Enter the customer's name (letters only, 2-80 characters)."
    clean["customer_name"] = name

    email = _text(data, "customer_email").lower()
    if len(email) > 120 or not EMAIL_PATTERN.match(email):
        errors["customer_email"] = "Enter a valid email address."
    clean["customer_email"] = email

    phone_digits = re.sub(r"\D", "", _text(data, "customer_phone"))
    if phone_digits and len(phone_digits) != 10:
        errors["customer_phone"] = "Phone number should be 10 digits, or leave it blank."
    clean["customer_phone"] = phone_digits

    city = _text(data, "city")
    if not CITY_PATTERN.match(city):
        errors["city"] = "Enter the job site's city."
    clean["city"] = city

    state = _text(data, "state").upper()
    if state not in US_STATES:
        errors["state"] = "Choose a state."
    clean["state"] = state

    clean["travel_miles"] = _number(
        data, "travel_miles", errors, "Travel distance", 0, MAX_TRAVEL_MILES
    )

    terrain = _text(data, "terrain")
    if terrain not in TERRAIN:
        errors["terrain"] = "Choose a terrain type."
    clean["terrain"] = terrain

    frequency = _text(data, "frequency")
    if frequency not in FREQUENCY:
        errors["frequency"] = "Choose how often the job repeats."
    clean["frequency"] = frequency

    notes = _text(data, "notes")
    if len(notes) > 500:
        errors["notes"] = "Notes must be 500 characters or fewer."
    clean["notes"] = notes

    quantities = {}
    for key, service in SERVICES.items():
        field = f"qty_{key}"
        quantities[key] = _number(data, field, errors, service["label"], 0, service["max"])
    if not any(quantities.values()) and not any(k.startswith("qty_") for k in errors):
        errors["services"] = "Add a quantity for at least one service."
    clean["quantities"] = quantities

    return clean, errors


def validate_status(value):
    return value if value in STATUSES else None
