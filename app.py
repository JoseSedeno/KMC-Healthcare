# 1. PAGE CONFIG
import streamlit as st

st.set_page_config(
    page_title="PBS Price Calculator",
    layout="wide"
)

# 2. CONSTANTS
SECTION_OPTIONS = ["Section 85"]
PRICE_TYPE_OPTIONS = ["AEMP", "DPMQ"]

# 3. INPUT SECTION – LEFT SIDE
left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.markdown("### PBS Price Calculator")

    selected_section = st.selectbox("Section", SECTION_OPTIONS)

    price_type = st.radio("Price type:", PRICE_TYPE_OPTIONS, horizontal=True)

    price_label = "AEMP price:" if price_type == "AEMP" else "DPMQ price:"
    input_price = st.number_input(price_label, min_value=0.0, step=0.01, format="%.2f")

    col1, col2 = st.columns(2)
    with col1:
        pricing_qty = st.number_input("Pricing quantity:", min_value=1, step=1, format="%d")
    with col2:
        max_qty = st.number_input("Maximum quantity:", min_value=1, step=1, format="%d")

    include_dangerous_fee = st.toggle("Include dangerous drug fee?")

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

# 4. CALCULATION FUNCTIONS

def calculate_aemp_max_qty(input_price, pricing_qty, max_qty):
    if pricing_qty == 0:  # avoid division by zero
        return 0.0
    return (input_price * max_qty) / pricing_qty


def calculate_wholesale_markup(aemp_max_qty):
    if aemp_max_qty <= 5.50:
        return 0.41
    elif aemp_max_qty <= 720.00:
        return aemp_max_qty * 0.0752
    else:
        return 54.14


def calculate_price_to_pharmacist(aemp_max_qty, wholesale_markup):
    return aemp_max_qty + wholesale_markup


def calculate_ahi_fee(price_to_pharmacist):
    if price_to_pharmacist < 100:
        return 4.79
    elif price_to_pharmacist <= 2000:
        return 4.79 + 0.05 * (price_to_pharmacist - 100)
    else:
        return 99.79  # 4.79 + 95


def calculate_dpmq(price_to_pharmacist, ahi_fee, include_dangerous=False):
    dispensing_fee = 8.67
    dangerous_fee = 4.46 if include_dangerous else 0.0
    return price_to_pharmacist + ahi_fee + dispensing_fee + dangerous_fee

# 5. RIGHT PANEL – OUTPUT BREAKDOWN

with right_col:
    st.markdown("### 💰 COST BREAKDOWN")

    aemp_max_qty = calculate_aemp_max_qty(input_price, pricing_qty, max_qty)
    wholesale_markup = calculate_wholesale_markup(aemp_max_qty)
    price_to_pharmacist = calculate_price_to_pharmacist(aemp_max_qty, wholesale_markup)
    ahi_fee = calculate_ahi_fee(price_to_pharmacist)
    dpmq = calculate_dpmq(price_to_pharmacist, ahi_fee, include_dangerous_fee)

    st.write(f"**AEMP:** ${input_price:.2f}")
    st.write(f"**AEMP for maximum quantity:** ${aemp_max_qty:.2f}")
    st.write(f"+ **Wholesale markup:** + ${wholesale_markup:.2f}")
    st.write(f"**Price to pharmacists:** ${price_to_pharmacist:.2f}")
    st.write(f"+ **Administration, handling and infrastructure (AHI) fee:** + ${ahi_fee:.2f}")
    st.write(f"+ **Dispensing fee:** + $8.67")
    if include_dangerous_fee:
        st.write(f"+ **Dangerous drug fee:** + $4.46")

    st.markdown(f"### 💊 **DPMQ: ${dpmq:.2f}**")


