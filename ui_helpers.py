# ui_helpers.py
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import streamlit as st

# ----- tiny local helpers -----
def to_decimal(value):
    return Decimal(str(value))

def validate_calculation_precision_enhanced(original_dpmq, reconstructed_dpmq, tolerance=Decimal("0.005")):
    original_dpmq = to_decimal(original_dpmq)
    reconstructed_dpmq = to_decimal(reconstructed_dpmq)
    diff = abs(original_dpmq - reconstructed_dpmq)
    if diff <= tolerance:
        return True, f"✅ Precision validated: difference ${diff:.4f}"
    else:
        return False, f"❌ Precision warning: difference ${diff:.4f} exceeds tolerance ${tolerance:.4f}"

# ----- formatting -----
def format_currency(amount):
    return f"${to_decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

# ----- data for download -----
def generate_cost_breakdown_df(
    aemp_max_qty, unit_aemp, wholesale_markup,
    price_to_pharmacist, ahi_fee, dispensing_fee,
    dangerous_fee, final_price, label="AEMP"
):
    data = [["AEMP for max quantity", format_currency(aemp_max_qty)]]
    if unit_aemp is not None:
        data.append(["Unit AEMP", format_currency(unit_aemp)])
    data.extend([
        ["Wholesale markup", format_currency(wholesale_markup)],
        ["Price to pharmacist", format_currency(price_to_pharmacist)],
        ["AHI fee", format_currency(ahi_fee)],
        ["Dispensing fee", format_currency(dispensing_fee)],
    ])
    if to_decimal(dangerous_fee) > 0:
        data.append(["Dangerous drug fee", format_currency(dangerous_fee)])

    label_row = "DPMQ" if label == "DPMQ" else "Final Price"
    data.append([label_row, format_currency(final_price)])

    return pd.DataFrame(data, columns=["Component", "Amount"])

# ----- on-screen breakdown -----
def display_cost_breakdown(
    aemp_max_qty, unit_aemp, wholesale_markup,
    price_to_pharmacist, ahi_fee, dispensing_fee,
    dangerous_fee, final_price, label="AEMP"
):
    st.markdown(f"### 💰 COST BREAKDOWN ({label})")
    st.write(f"**AEMP for max quantity:** {format_currency(aemp_max_qty)}")
    if unit_aemp is not None:
        st.write(f"**Unit AEMP:** {format_currency(unit_aemp)}")
    st.write(f"**Wholesale markup:** {format_currency(wholesale_markup)}")
    st.write(f"**Price to pharmacist:** {format_currency(price_to_pharmacist)}")
    st.write(f"**AHI fee:** {format_currency(ahi_fee)}")
    st.write(f"**Dispensing fee:** {format_currency(dispensing_fee)}")
    if to_decimal(dangerous_fee) > 0:
        st.write(f"**Dangerous drug fee:** {format_currency(dangerous_fee)}")

    dpmq_label = "Reconstructed DPMQ" if label == "DPMQ" else "DPMQ"
    st.markdown(f"### 💊 {dpmq_label}: **{format_currency(final_price)}**")

    # only validate when showing inverse (label == "DPMQ")
    if label == "DPMQ":
        original_dpmq = st.session_state.get("original_input_price", final_price)
        is_valid, message = validate_calculation_precision_enhanced(original_dpmq, final_price)
        (st.success if is_valid else st.error)(message)
