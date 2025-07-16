# ===============================
# SECTION 85 – CORE SETUP
# ===============================

# 1. PAGE CONFIGURATION
import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP, getcontext
import io
import os

# Optional: Ensures Excel export works (can be removed if handled in requirements.txt)
os.system("pip install xlsxwriter")

# Set decimal precision for PBS calculations
getcontext().prec = 10

# Configure Streamlit layout and metadata
st.set_page_config(
    page_title="PBS Price Calculator",
    layout="wide"
)

# ===============================
# 2. GLOBAL CONSTANTS – SECTION 85
# ===============================

# Currently implemented section
SECTION_OPTIONS = ["Section 85"]

# Pricing logic options
PRICE_TYPE_OPTIONS = ["AEMP", "DPMQ"]

# 3. 📥 SECTION 85 – INPUT SECTION (LEFT SIDE)

left_col, right_col = st.columns([1, 1.2])

with left_col:

    # ------------------------------
    # 🔹 User Selections
    # ------------------------------
    st.markdown("### PBS Price Calculator")

    selected_section = st.selectbox("Section", SECTION_OPTIONS)

    price_type = st.radio("Price type:", PRICE_TYPE_OPTIONS, horizontal=True)
    price_label = "AEMP price:" if price_type == "AEMP" else "DPMQ price:"
    input_price = st.number_input(price_label, min_value=0.0, step=0.01, format="%.2f")

    # ------------------------------
    # 🔹 Input Validations
    # ------------------------------
    MIN_DPMQ = Decimal("13.88")
    if price_type == "DPMQ" and Decimal(input_price) < MIN_DPMQ:
        st.error("❌ DPMQ too low. It must be at least $13.88 to cover mandatory PBS fees.")
        st.stop()

    # ------------------------------
    # 🔹 Quantities
    # ------------------------------
    col1, col2 = st.columns(2)
    with col1:
        pricing_qty = st.number_input("Pricing quantity:", min_value=1, step=1, format="%d")
    with col2:
        max_qty = st.number_input("Maximum quantity:", min_value=1, step=1, format="%d")

    # ------------------------------
    # 🔹 Additional Options
    # ------------------------------
    include_dangerous_fee = st.toggle("Include dangerous drug fee?")

    DISPENSING_OPTIONS = ["Ready-prepared"]
    dispensing_type = st.selectbox("Dispensing type:", DISPENSING_OPTIONS)

    # ------------------------------
    # 🔹 Footer Notes
    # ------------------------------
    st.markdown("""
    <div style='font-size: 12px; color: grey; margin-top: 20px;'>
        There might be slight discrepancy in the estimated DPMQ values from the calculator and published DPMQ prices due to rounding of values.  
        Last updated: 1 July 2024
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='margin-top: 20px; font-size: 12px; color: grey;'>
        Co-developed by: <strong>KMC Healthcare</strong>
    </div>
    """, unsafe_allow_html=True)


# 4. 📦 SECTION 85 – CALCULATION FUNCTIONS

from decimal import Decimal, ROUND_HALF_UP

# ----------------------
# 🔹 FORWARD LOGIC
# ----------------------

# Forward: AEMP (unit) → AEMP (max quantity)
def calculate_aemp_max_qty(input_price, pricing_qty, max_qty):
    if pricing_qty == 0:
        return Decimal("0.00")
    return (Decimal(input_price) * Decimal(max_qty)) / Decimal(pricing_qty)

# Forward: AHI Fee – FORWARD PBS LOGIC
def calculate_ahi_fee(price_to_pharmacist):
    price_to_pharmacist = Decimal(price_to_pharmacist)
    if price_to_pharmacist < Decimal("100"):
        return Decimal("4.79")
    elif price_to_pharmacist <= Decimal("2000"):
        return Decimal("4.79") + Decimal("0.05") * (price_to_pharmacist - Decimal("100"))
    else:
        return Decimal("99.79")

# Forward: DPMQ = PtP + AHI + Dispensing + [Dangerous]
def calculate_dpmq(price_to_pharmacist, ahi_fee, include_dangerous=False):
    dispensing_fee = Decimal("8.67")
    dangerous_fee = Decimal("4.46") if include_dangerous else Decimal("0.00")
    return Decimal(price_to_pharmacist) + Decimal(ahi_fee) + dispensing_fee + dangerous_fee

# ----------------------
# 🔹 INVERSE TIER LOGIC
# ----------------------

def get_wholesale_tier(dpmq):
    dpmq = Decimal(dpmq)
    if dpmq <= Decimal("19.37"):
        return "Tier1"
    elif dpmq <= Decimal("821.31"):
        return "Tier2"
    else:
        return "Tier3"

def get_inverse_tier_type(dpmq):
    return get_wholesale_tier(dpmq)

# ----------------------
# 🔹 INVERSE CALCULATOR – PRECISION AEMP LOGIC
# ----------------------

def precise_inverse_aemp(dpmq, dispensing_fee):
    dpmq = Decimal(dpmq)
    dispensing_fee = Decimal(dispensing_fee)

    low = Decimal("0.01")
    high = Decimal("1000000.00")  # ✅ supports pills up to $1M
    tolerance = Decimal("0.00005")  # 🔧 Tighter tolerance for cent-perfect DPMQ

    best_aemp = None
    closest_diff = None

    while low <= high:
        mid = (low + high) / 2

        # Wholesale markup
        if mid <= Decimal("5.50"):
            wholesale = Decimal("0.41")
        elif mid <= Decimal("720.00"):
            wholesale = mid * Decimal("0.0752")
        else:
            wholesale = Decimal("54.14")

        ptp = mid + wholesale

        # AHI Fee
        if ptp <= Decimal("100.00"):
            ahi = Decimal("4.79")
        elif ptp <= Decimal("2000.00"):
            ahi = Decimal("4.79") + (ptp - Decimal("100.00")) * Decimal("0.05")
        else:
            ahi = Decimal("99.79")

        reconstructed_dpmq = ptp + ahi + dispensing_fee
        diff = abs(reconstructed_dpmq - dpmq)

        if closest_diff is None or diff < closest_diff:
            closest_diff = diff
            best_aemp = mid

        if diff <= tolerance:
            break

        if reconstructed_dpmq < dpmq:
            low = mid + Decimal("0.00001")  # 🔧 finer step for high precision
        else:
            high = mid - Decimal("0.00001")

    return best_aemp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# Tiered logic controller
def calculate_inverse_aemp_max(dpmq, dispensing_fee, tier):
    dpmq = Decimal(dpmq)
    dispensing_fee = Decimal(dispensing_fee)

    if tier == "Tier1":
        return dpmq - dispensing_fee - Decimal("4.79") - Decimal("0.41")
    elif tier in ("Tier2", "Tier3"):
        return precise_inverse_aemp(dpmq, dispensing_fee)
    return Decimal("0.00")  # fallback

# ----------------------
# 🔹 HELPER CALCULATIONS
# ----------------------

# AEMP (max qty) → Unit AEMP
def calculate_unit_aemp(aemp_max_qty, pricing_qty, max_qty):
    if max_qty == 0:
        return Decimal("0.00")
    return (Decimal(aemp_max_qty) * Decimal(pricing_qty)) / Decimal(max_qty)

# Inverse: Wholesale markup from AEMP
def calculate_inverse_wholesale_markup(aemp_max_qty):
    aemp_max_qty = Decimal(aemp_max_qty)
    if aemp_max_qty <= Decimal("5.50"):
        return Decimal("0.41")
    elif aemp_max_qty <= Decimal("720.00"):
        return aemp_max_qty * Decimal("0.0752")
    else:
        return Decimal("54.14")

# AEMP + markup = PTP
def calculate_price_to_pharmacist(aemp_max_qty, wholesale_markup):
    return Decimal(aemp_max_qty) + Decimal(wholesale_markup)

# Inverse: AHI Fee – based on PtP
def calculate_inverse_ahi_fee(price_to_pharmacist):
    price_to_pharmacist = Decimal(price_to_pharmacist)
    if price_to_pharmacist <= Decimal("100.00"):
        return Decimal("4.79")
    elif price_to_pharmacist <= Decimal("2000.00"):
        return Decimal("4.79") + (price_to_pharmacist - Decimal("100.00")) * Decimal("0.05")
    else:
        return Decimal("99.79")

# Final DPMQ – used in inverse check
def calculate_inverse_dpmq(price_to_pharmacist, ahi_fee, dispensing_fee, include_dangerous=False):
    dangerous_fee = Decimal("4.46") if include_dangerous else Decimal("0.00")
    return Decimal(price_to_pharmacist) + Decimal(ahi_fee) + Decimal(dispensing_fee) + dangerous_fee

# ----------------------
# 🔹 COST BREAKDOWN (Visuals & Exports)
# ----------------------

def generate_cost_breakdown_df(
    aemp_max_qty, unit_aemp, wholesale_markup,
    price_to_pharmacist, ahi_fee, dispensing_fee,
    dangerous_fee, final_price, label="AEMP"
):
    data = [["AEMP for max quantity", f"${Decimal(aemp_max_qty):.2f}"]]

    if unit_aemp is not None:
        data.append(["Unit AEMP", f"${Decimal(unit_aemp):.2f}"])

    data.extend([
        ["Wholesale markup", f"${Decimal(wholesale_markup):.2f}"],
        ["Price to pharmacist", f"${Decimal(price_to_pharmacist):.2f}"],
        ["AHI fee", f"${Decimal(ahi_fee):.2f}"],
        ["Dispensing fee", f"${Decimal(dispensing_fee):.2f}"]
    ])

    if Decimal(dangerous_fee) > 0:
        data.append(["Dangerous drug fee", f"${Decimal(dangerous_fee):.2f}"])

    label_row = "DPMQ" if label == "DPMQ" else "Final Price"
    data.append([label_row, f"${Decimal(final_price):.2f}"])

    return pd.DataFrame(data, columns=["Component", "Amount"])


def display_cost_breakdown(
    aemp_max_qty, unit_aemp, wholesale_markup,
    price_to_pharmacist, ahi_fee, dispensing_fee,
    dangerous_fee, final_price, label="AEMP"
):
    st.markdown(f"### 💰 COST BREAKDOWN ({label})")
    st.write(f"**AEMP for max quantity:** ${Decimal(aemp_max_qty):.2f}")
    if unit_aemp is not None:
        st.write(f"**Unit AEMP:** ${Decimal(unit_aemp):.2f}")
    st.write(f"**Wholesale markup:** ${Decimal(wholesale_markup):.2f}")
    st.write(f"**Price to pharmacist:** ${Decimal(price_to_pharmacist):.2f}")
    st.write(f"**AHI fee:** ${Decimal(ahi_fee):.2f}")
    st.write(f"**Dispensing fee:** ${Decimal(dispensing_fee):.2f}")
    if Decimal(dangerous_fee) > 0:
        st.write(f"**Dangerous drug fee:** ${Decimal(dangerous_fee):.2f}")
    st.markdown(f"### 💊 {'Reconstructed DPMQ' if label == 'DPMQ' else 'DPMQ'}: **${Decimal(final_price):.2f}**")


# 5. 📤 SECTION 85 – OUTPUT BREAKDOWN

# ----------------------------------------
# 🔹 Forward Wholesale Markup (AEMP to PtP)
# ----------------------------------------

def calculate_wholesale_markup(aemp_max_qty):
    aemp_max_qty = Decimal(aemp_max_qty)
    if aemp_max_qty <= Decimal("5.50"):
        return Decimal("0.41")
    elif aemp_max_qty <= Decimal("720.00"):
        return aemp_max_qty * Decimal("0.0752")
    else:
        return Decimal("54.14")


# ----------------------------------------
# 🔹 SECTION 85 – RIGHT PANEL OUTPUT LOGIC
# ----------------------------------------

with right_col:

    # ------------------------------
    # 🔁 INVERSE CALCULATOR (DPMQ → AEMP)
    # ------------------------------
    if price_type == "DPMQ":
        dispensing_fee = Decimal("8.67")
        tier = get_inverse_tier_type(input_price)

        # Inverse: DPMQ → AEMP
        aemp_max_qty = calculate_inverse_aemp_max(input_price, dispensing_fee, tier)
        unit_aemp = calculate_unit_aemp(aemp_max_qty, pricing_qty, max_qty)
        wholesale_markup = calculate_inverse_wholesale_markup(aemp_max_qty)
        price_to_pharmacist = calculate_price_to_pharmacist(aemp_max_qty, wholesale_markup)
        ahi_fee = calculate_inverse_ahi_fee(price_to_pharmacist)
        dangerous_fee = Decimal("4.46") if include_dangerous_fee else Decimal("0.00")

        dpmq = price_to_pharmacist + ahi_fee + dispensing_fee + dangerous_fee

        st.markdown("### 🧮 COST BREAKDOWN (Inverse)")
        st.write(f"**Tier used:** {tier}")
        st.write(f"**AEMP for max quantity:** ${aemp_max_qty:.2f}")

        display_cost_breakdown(
            aemp_max_qty, unit_aemp, wholesale_markup,
            price_to_pharmacist, ahi_fee, dispensing_fee,
            dangerous_fee, dpmq, label="DPMQ"
        )

        # Export – Inverse
        df = generate_cost_breakdown_df(
            aemp_max_qty, unit_aemp, wholesale_markup,
            price_to_pharmacist, ahi_fee, dispensing_fee,
            dangerous_fee, dpmq, label="DPMQ"
        )
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Cost Breakdown")

        st.download_button(
            label="📥 Download DPMQ Breakdown as Excel",
            data=buffer.getvalue(),
            file_name="dpmpq_breakdown.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    # ------------------------------
    # 🔄 FORWARD CALCULATOR (AEMP → DPMQ)
    # ------------------------------
    elif price_type == "AEMP":
        dispensing_fee = Decimal("8.67")

        # Forward: AEMP → DPMQ
        aemp_max_qty = calculate_aemp_max_qty(input_price, pricing_qty, max_qty)
        wholesale_markup = calculate_wholesale_markup(aemp_max_qty)
        price_to_pharmacist = calculate_price_to_pharmacist(aemp_max_qty, wholesale_markup)
        ahi_fee = calculate_ahi_fee(price_to_pharmacist)
        dangerous_fee = Decimal("4.46") if include_dangerous_fee else Decimal("0.00")

        dpmq = calculate_dpmq(price_to_pharmacist, ahi_fee, include_dangerous_fee)

        display_cost_breakdown(
            aemp_max_qty, None, wholesale_markup,
            price_to_pharmacist, ahi_fee, dispensing_fee,
            dangerous_fee, dpmq, label="AEMP"
        )

        # Export – Forward
        df = generate_cost_breakdown_df(
            aemp_max_qty, None, wholesale_markup,
            price_to_pharmacist, ahi_fee, dispensing_fee,
            dangerous_fee, dpmq, label="AEMP"
        )
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Cost Breakdown")

        st.download_button(
            label="📥 Download AEMP Breakdown as Excel",
            data=buffer.getvalue(),
            file_name="aemp_breakdown.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )



