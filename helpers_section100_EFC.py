# helpers_section100.py

from decimal import Decimal, ROUND_HALF_UP
from config import PBS_CONSTANTS

def calculate_unit_aemp(aemp_max_qty, pricing_qty, max_amount):
    """Calculate unit AEMP"""
    return Decimal(aemp_max_qty) * Decimal(pricing_qty) / Decimal(max_amount)

def calculate_wholesale_markup_private(aemp_max_qty):
    """Apply 1.4% markup only for private hospitals"""
    return Decimal(aemp_max_qty) * Decimal("0.014")

def calculate_ahi_fee(hospital_setting, ptp):
    """Apply AHI Fee depending on hospital type"""
    if hospital_setting == "Public":
        return ptp * Decimal("0.2197")
    else:  # Private
        return ptp * Decimal("0.3994")

def run_section100_efc_forward(input_price, pricing_qty, vial_content, max_amount, consider_wastage, hospital_setting):
    aemp = Decimal(input_price)
    max_amount = Decimal(max_amount)
    pricing_qty = Decimal(pricing_qty)

    # Step 1: Calculate AEMP for max amount
    aemp_max_qty = aemp * max_amount / pricing_qty

    # Step 2: Apply markup (only if private)
    if hospital_setting == "Private":
        wholesale_markup = calculate_wholesale_markup_private(aemp_max_qty)
    else:
        wholesale_markup = Decimal("0.00")

    ptp = aemp_max_qty + wholesale_markup

    # Step 3: Apply AHI Fee (Public or Private)
    ahi_fee = calculate_ahi_fee(hospital_setting, ptp)

    # Step 4: Final DPMA
    dpma = ptp + ahi_fee

    # Optional unit AEMP
    unit_aemp = aemp_max_qty * pricing_qty / max_amount

    return {
        "aemp": aemp,
        "aemp_max_qty": aemp_max_qty,
        "unit_aemp": unit_aemp,
        "wholesale_markup": wholesale_markup,
        "price_to_pharmacist": ptp,
        "ahi_fee": ahi_fee,
        "dpma": dpma
    }
