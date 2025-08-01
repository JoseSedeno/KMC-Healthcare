# helpers_section100_EFC.py

from decimal import Decimal, ROUND_HALF_UP
from config import PBS_CONSTANTS
import math
import streamlit as st
import pandas as pd
import io
from app import display_cost_breakdown, generate_cost_breakdown_df

# ----------------------------
# 🔹 AEMP → DPMQ (Forward Logic)
# ----------------------------

def calculate_unit_aemp(aemp_max_qty, pricing_qty, max_amount):
    return Decimal(aemp_max_qty) * Decimal(pricing_qty) / Decimal(max_amount)

def calculate_wholesale_markup_private(aemp_max_qty):
    return Decimal(aemp_max_qty) * Decimal("0.014")

def calculate_ahi_fee_fixed(hospital_setting):
    if hospital_setting == "Public":
        return Decimal("90.13")
    else:
        return Decimal("134.80")

def run_section100_efc_forward(input_price, pricing_qty, vial_content, max_amount, consider_wastage, hospital_setting):
    aemp = Decimal(input_price)
    pricing_qty = Decimal(pricing_qty)
    max_amount = Decimal(max_amount)

    aemp_max_qty = aemp * max_amount / pricing_qty

    if hospital_setting == "Private":
        wholesale_markup = calculate_wholesale_markup_private(aemp_max_qty)
    else:
        wholesale_markup = Decimal("0.00")

    ptp = aemp_max_qty + wholesale_markup
    ahi_fee = calculate_ahi_fee_fixed(hospital_setting)
    dpma = ptp + ahi_fee

    unit_aemp = aemp_max_qty * pricing_qty / max_amount

    display_cost_breakdown(
        aemp_max_qty=aemp_max_qty,
        unit_aemp=unit_aemp,
        wholesale_markup=wholesale_markup,
        price_to_pharmacist=ptp,
        ahi_fee=ahi_fee,
        dispensing_fee=Decimal("0.00"),
        dangerous_fee=Decimal("0.00"),
        final_price=dpma,
        label="AEMP"
    )

    df = generate_cost_breakdown_df(
        aemp_max_qty, unit_aemp, wholesale_markup,
        ptp, ahi_fee,
        Decimal("0.00"), Decimal("0.00"),
        dpma, label="AEMP"
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Cost Breakdown")

    st.download_button(
        label="📅 Download AEMP Breakdown in Excel",
        data=buffer.getvalue(),
        file_name="section100_forward_aemp.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ----------------------------
# 🔁 DPMQ → AEMP (Inverse Logic)
# ----------------------------

def calculate_ahi_fee_efc(hospital_setting):
    if hospital_setting == "Public":
        return Decimal("90.13")
    else:
        return Decimal("134.80")

def calculate_vials_needed(max_amount, vial_content, consider_wastage):
    max_amount = Decimal(max_amount)
    vial_content = Decimal(vial_content)

    if consider_wastage:
        return math.ceil(max_amount / vial_content)
    else:
        return max_amount / vial_content

def run_section100_efc_inverse(input_price, pricing_qty, vial_content, max_amount, consider_wastage, hospital_setting):
    st.session_state['original_input_price'] = input_price
    dpmq_input = Decimal(input_price)

    # Step 1: Remove AHI Fee
    ahi_fee = calculate_ahi_fee_efc(hospital_setting)
    subtotal = dpmq_input - ahi_fee

    # Step 2: Remove wholesale markup
    if hospital_setting == "Private":
        price_to_pharmacist = subtotal / Decimal("1.014")
        markup = subtotal - price_to_pharmacist
    else:
        price_to_pharmacist = subtotal
        markup = Decimal("0.00")

    # Step 3: Reconstruct AEMP (total → unit)
    vials_needed = calculate_vials_needed(max_amount, vial_content, consider_wastage)
    total_aemp = price_to_pharmacist * Decimal(pricing_qty)
    aemp_max_qty = total_aemp / Decimal(vials_needed)

    # Final output
    display_cost_breakdown(
        aemp_max_qty=aemp_max_qty,
        unit_aemp=None,
        wholesale_markup=markup,
        price_to_pharmacist=price_to_pharmacist,
        ahi_fee=ahi_fee,
        dispensing_fee=Decimal("0.00"),
        dangerous_fee=Decimal("0.00"),
        final_price=dpmq_input,
        label="DPMQ"
    )

    df = generate_cost_breakdown_df(
        aemp_max_qty, None, markup,
        price_to_pharmacist, ahi_fee,
        Decimal("0.00"), Decimal("0.00"),
        dpmq_input, label="DPMQ"
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Cost Breakdown")

    st.download_button(
        label="📅 Download DPMQ Breakdown in Excel",
        data=buffer.getvalue(),
        file_name="section100_inverse_dpmq.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
