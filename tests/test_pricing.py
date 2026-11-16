from decimal import Decimal

from pricing import calculate_quote, travel_fee


def test_travel_fee_tiers():
    assert travel_fee(0) == Decimal("0.00")
    assert travel_fee(10) == Decimal("0.00")
    assert travel_fee(10.5) == Decimal("35.00")
    assert travel_fee(40) == Decimal("60.00")
    assert travel_fee(50) == Decimal("77.50")


def test_mowing_only_flat_one_time():
    result = calculate_quote({"mowing": 20}, "flat", "one_time", 0)
    assert result["labor_total"] == Decimal("275.00")
    assert result["material_total"] == Decimal("0.00")
    assert result["tax"] == Decimal("0.00")
    assert result["total"] == Decimal("275.00")
    assert result["deposit"] == Decimal("0.00")


def test_materials_marked_up_and_taxed():
    result = calculate_quote({"mulch": 10}, "flat", "one_time", 0)
    assert result["material_total"] == Decimal("475.00")
    assert result["tax"] == Decimal("42.75")
    assert result["labor_total"] == Decimal("412.50")
    assert result["total"] == Decimal("930.25")
    assert result["deposit"] == Decimal("279.08")


def test_terrain_and_weekly_discount_apply_to_labor_only():
    result = calculate_quote({"mowing": 20}, "steep", "weekly", 0)
    assert result["labor_total"] == Decimal("371.25")
    assert result["discount"] == Decimal("37.13")
    assert result["total"] == Decimal("334.12")


def test_minimum_job_charge():
    result = calculate_quote({"hedge": 10}, "flat", "one_time", 0)
    assert result["subtotal"] == Decimal("75.00")
    assert result["minimum_adjustment"] > 0


def test_crew_days_rounds_up():
    result = calculate_quote({"irrigation": 10}, "flat", "one_time", 0)
    assert result["labor_hours"] == 25.0
    assert result["crew_days"] == 2
