# helpers_section100_EFC.py

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Optional
import math
import io

import pandas as pd
import streamlit as st

from config import PBS_CONSTANTS  # keep available if you expand logic
from ui_helpers import display_cost_breakdown, generate_cost_breakdown_df

# Tighter precision for financial math
getcontext().prec = 28

# ==============================
# Utilities
# ==============================

MONEY = Decimal("0.01")


def D(x) -> Decimal:
    """Safe Decimal conversion."""
    return Decimal(str(x))


def q(amount: Decimal) -> Decimal:
    """Quantize to cents (half up)."""
    return amount.quantize(MONEY, rounding=ROUND_HALF_UP)


def _validate_positive(name: str, value) -> None:
    if D(value) <= 0:
        st.error(f"❌ {name} must be greater than zero.")
        st.stop()


# ==============================
# Core Calculators (S100 EFC)
# ==============================

def calculate_unit_aemp(aemp_max_qty: Decimal, pricing_qty: Decimal, max_amount: Decimal) -> Decimal:
    """
    Unit AEMP = AEMP(max amount) * pricing_qty / max_amount
    Keeps full precision; caller can round if desired.
    """
    return D(aemp_max_qty) * D(pricing_qty) / D(max_amount)


def calculate_wholesale_markup_private(aemp_max_qty: Decimal) -> Decimal:
    """
    Private hospital add-on: 1.4 percent of AEMP at maximum amount.
    """
    return D(aemp_max_qty) * D("0.014")


def calculate_ahi_fee_fixed(hospital_setting: str) -> Decimal:
    """
    Fixed AHI fee by setting.
    Public:  90.13
    Private: 134.80
    """
    return D("90.13") if hospital_setting == "Public" else D("134.80")


def calculate_ahi_fee_efc(hospital_setting: str) -> Decimal:
    """Alias used by inverse path."""
    return calculate_ahi_fee_fixed(hospital_setting)


def calculate_vials_needed(max_amount: Decimal, vial_content: Decimal, consider_wastage: bool) -> Decimal:
    """
    If wastage is considered, round vials up to the next whole vial.
    If not, allow fractional vials.
    """
    max_amount = D(max_amount)
    vial_content = D(vial_content)

    if consider_wastage:
        return D(math.ceil(max_amount / vial_content))
    return max_amount / vial_content


# ==============================
# Forward: AEMP -> DPMA (shown as DPMQ label in UI)
# ==============================

def run_section100_efc_forward(
    input_price,
    pricing_qty,
    vial_content,
    max_amount,
    consider_wastage: bool,
    hospital_setting: str
) -> None:
    """
    Forward path for Section 100 EFC:
      INPUT  : unit AEMP (ex-manufacturer)
      OUTPUT : DPMA (PtP + AHI; no dispensing or dangerous fees for EFC)
    """

    # Basic validation
    _validate_positive("Pricing quantity", pricing_qty)
    _validate_positive("Maximum amount (mg)", max_amount)
    _validate_positive("Vial content (mg)", vial_content)

    aemp_unit = D(input_price)
    pricing_qty = D(pricing_qty)
    max_amount = D(max_amount)

    # AEMP for maximum amount
    aemp_max_qty = aemp_unit * max_amount / pricing_qty

    # Private wholesale markup
    if hospital_setting == "Private":
        wholesale_markup = calculate_wholesale_markup_private(aemp_max_qty)
    else:
        wholesale_markup = D("0.00")

    # PtP analogue
    ptp = aemp_max_qty + wholesale_markup

    # Fixed AHI fee by setting
    ahi_fee = calculate_ahi_fee_fixed(hospital_setting)

    # Final DPMA
    dpma = ptp + ahi_fee

    # Also show unit AEMP back to the user
    unit_aemp = calculate_unit_aemp(aemp_max_qty, pricing_qty, max_amount)

    # UI breakdown
    display_cost_breakdown(
        aemp_max_qty=q(aemp_max_qty),
        unit_aemp=q(unit_aemp),
        wholesale_markup=q(wholesale_markup),
        price_to_pharmacist=q(ptp),
        ahi_fee=q(ahi_fee),
        dispensing_fee=D("0.00"),
        dangerous_fee=D("0.00"),
        final_price=q(dpma),
        label="AEMP",
    )

    # Download breakdown (Excel)
    df = generate_cost_breakdown_df(
        q(aemp_max_qty), q(unit_aemp), q(wholesale_markup),
        q(ptp), q(ahi_fee),
        D("0.00"), D("0.00"),
        q(dpma), label="AEMP"
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Cost Breakdown")

    st.download_button(
        label="📥 Download AEMP to DPMA breakdown (Excel)",
        data=buffer.getvalue(),
        file_name="section100_forward_aemp.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ==============================
# Inverse: DPMA -> AEMP
# ==============================

def run_section100_efc_inverse(
    input_price,
    pricing_qty,
    vial_content,
    max_amount,
    consider_wastage: bool,
    hospital_setting: str
) -> None:
    """
    Inverse path for Section 100 EFC:
      INPUT  : DPMA (shown as DPMQ in the shared UI)
      OUTPUT : AEMP(max amount) and components, plus downloadable breakdown
    Steps:
      1) Remove fixed AHI fee for the selected setting.
      2) If Private, remove 1.4 percent markup (divide by 1.014).
      3) Reconstruct AEMP(max amount). If wastage is ON, use whole vials; else allow fractional vials.
    """

    # Stash input for on-screen precision checks
    st.session_state["original_input_price"] = input_price

    # Basic validation
    _validate_positive("Pricing quantity", pricing_qty)
    _validate_positive("Maximum amount (mg)", max_amount)
    _validate_positive("Vial content (mg)", vial_content)

    dpmq_input = D(input_price)  # DPMA in S100 wording

    # 1) Remove fixed AHI
    ahi_fee = calculate_ahi_fee_efc(hospital_setting)
    subtotal = dpmq_input - ahi_fee

    # 2) Remove wholesale markup for private setting
    if hospital_setting == "Private":
        # subtotal = PtP * 1.014  ->  PtP = subtotal / 1.014
        price_to_pharmacist = subtotal / D("1.014")
        markup = subtotal - price_to_pharmacist
    else:
        price_to_pharmacist = subtotal
        markup = D("0.00")

    # 3) Reconstruct AEMP(max)
    vials_needed = calculate_vials_needed(D(max_amount), D(vial_content), consider_wastage)

    if vials_needed == 0:
        aemp_max_qty = D("0.00")
    else:
        # price_to_pharmacist represents the total PtP for max amount.
        # To get AEMP(max) per pricing unit, scale by pricing_qty / vials.
        aemp_max_qty = (price_to_pharmacist * D(pricing_qty)) / D(vials_needed)

    # UI breakdown
    display_cost_breakdown(
        aemp_max_qty=q(aemp_max_qty),
        unit_aemp=None,
        wholesale_markup=q(markup),
        price_to_pharmacist=q(price_to_pharmacist),
        ahi_fee=q(ahi_fee),
        dispensing_fee=D("0.00"),
        dangerous_fee=D("0.00"),
        final_price=q(dpmq_input),
        label="DPMQ",
    )

    # Download breakdown (Excel)
    df = generate_cost_breakdown_df(
        q(aemp_max_qty), None, q(markup),
        q(price_to_pharmacist), q(ahi_fee),
        D("0.00"), D("0.00"),
        q(dpmq_input), label="DPMQ"
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Cost Breakdown")

    st.download_button(
        label="📥 Download DPMA to AEMP breakdown (Excel)",
        data=buffer.getvalue(),
        file_name="section100_inverse_dpmq.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
