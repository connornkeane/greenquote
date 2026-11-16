import math
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

LABOR_RATE = Decimal("55.00")
MATERIAL_MARKUP = Decimal("0.25")
SALES_TAX_RATE = Decimal("0.09")
MINIMUM_JOB = Decimal("75.00")
DEPOSIT_RATE = Decimal("0.30")
DEPOSIT_THRESHOLD = Decimal("500.00")
CREW_SIZE = 3
CREW_DAY_HOURS = 8

SERVICES = {
    "mowing": {
        "label": "Mowing & edging",
        "unit": "1,000 sq ft",
        "labor_hours": Decimal("0.25"),
        "material": Decimal("0.00"),
        "max": 500,
    },
    "cleanup": {
        "label": "Leaf & bed cleanup",
        "unit": "1,000 sq ft",
        "labor_hours": Decimal("0.60"),
        "material": Decimal("4.00"),
        "max": 300,
    },
    "mulch": {
        "label": "Mulch install",
        "unit": "cubic yard",
        "labor_hours": Decimal("0.75"),
        "material": Decimal("38.00"),
        "max": 200,
    },
    "hedge": {
        "label": "Hedge trimming",
        "unit": "linear ft",
        "labor_hours": Decimal("0.02"),
        "material": Decimal("0.00"),
        "max": 5000,
    },
    "sod": {
        "label": "Sod install",
        "unit": "sq ft",
        "labor_hours": Decimal("0.01"),
        "material": Decimal("0.55"),
        "max": 50000,
    },
    "irrigation": {
        "label": "Irrigation zone repair",
        "unit": "zone",
        "labor_hours": Decimal("2.50"),
        "material": Decimal("85.00"),
        "max": 40,
    },
}

TERRAIN = {
    "flat": {"label": "Flat / open", "multiplier": Decimal("1.00")},
    "moderate": {"label": "Moderate slope or obstacles", "multiplier": Decimal("1.15")},
    "steep": {"label": "Steep or tight access", "multiplier": Decimal("1.35")},
}

FREQUENCY = {
    "one_time": {"label": "One-time job", "discount": Decimal("0.00")},
    "biweekly": {"label": "Every two weeks", "discount": Decimal("0.05")},
    "weekly": {"label": "Weekly", "discount": Decimal("0.10")},
}

MAX_TRAVEL_MILES = 60


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def travel_fee(miles):
    miles = Decimal(str(miles))
    if miles <= 10:
        return Decimal("0.00")
    if miles <= 25:
        return Decimal("35.00")
    if miles <= 40:
        return Decimal("60.00")
    return money(Decimal("60.00") + (miles - 40) * Decimal("1.75"))


def calculate_quote(quantities, terrain, frequency, travel_miles):
    multiplier = TERRAIN[terrain]["multiplier"]
    discount_rate = FREQUENCY[frequency]["discount"]

    items = []
    labor_hours = Decimal("0")
    labor_total = Decimal("0")
    material_total = Decimal("0")

    for key, service in SERVICES.items():
        qty = Decimal(str(quantities.get(key, 0)))
        if qty <= 0:
            continue
        hours = service["labor_hours"] * qty * multiplier
        labor_cost = money(hours * LABOR_RATE)
        material_cost = money(service["material"] * qty * (1 + MATERIAL_MARKUP))
        labor_hours += hours
        labor_total += labor_cost
        material_total += material_cost
        items.append(
            {
                "service_key": key,
                "label": service["label"],
                "quantity": float(qty),
                "unit": service["unit"],
                "labor_cost": labor_cost,
                "material_cost": material_cost,
                "line_total": labor_cost + material_cost,
            }
        )

    discount = money(labor_total * discount_rate)
    travel = travel_fee(travel_miles)
    tax = money(material_total * SALES_TAX_RATE)
    subtotal = labor_total + material_total - discount + travel
    minimum_adjustment = Decimal("0.00")
    if subtotal < MINIMUM_JOB:
        minimum_adjustment = MINIMUM_JOB - subtotal
        subtotal = MINIMUM_JOB
    total = money(subtotal + tax)
    deposit = money(total * DEPOSIT_RATE) if total >= DEPOSIT_THRESHOLD else Decimal("0.00")
    crew_days = labor_hours / (CREW_SIZE * CREW_DAY_HOURS)

    return {
        "items": items,
        "labor_total": money(labor_total),
        "material_total": money(material_total),
        "discount": discount,
        "travel_fee": travel,
        "minimum_adjustment": money(minimum_adjustment),
        "subtotal": money(subtotal),
        "tax": tax,
        "total": total,
        "deposit": deposit,
        "labor_hours": float(round(labor_hours, 1)),
        "crew_days": max(1, math.ceil(crew_days)) if labor_hours > 0 else 0,
    }


def to_json_ready(result):
    ready = {}
    for key, value in result.items():
        if isinstance(value, Decimal):
            ready[key] = float(value)
        elif key == "items":
            ready[key] = [
                {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}
                for item in value
            ]
        else:
            ready[key] = value
    return ready
