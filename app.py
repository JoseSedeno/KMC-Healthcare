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
    <div style='margin-top: 20px;'>
        <span style='font-size: 12px;'>Co-developed by:</span><br>
        <img src='https://upload.wikimedia.org/wikipedia/commons/4/45/Lucid_logo.svg' width='100'>
        <img src='https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/Analytics_icon.svg/1200px-Analytics_icon.svg.png' width='80'>
    </div>
    """, unsafe_allow_html=True)

# 4. CALCULATION FUNCTIONS (PLACEHOLDER ONLY)
def calculate_aemp():
    return 0.00

def calculate_dpmq():
    return 0.00

# 5. RIGHT PANEL – OUTPUT BREAKDOWN
with right_col:
    st.markdown("### COST BREAKDOWN")

    st.button("Download", help="Export results", use_container_width=False)

    st.markdown("---")
    st.write("**AEMP:**", "$0.00")
    st.write("**AEMP for maximum quantity:**", "$0.00")
    st.write("**+ Wholesale markup:**", "+ $0.00")
    st.write("**Price to pharmacists:**", "$0.00")
    st.write("**+ Administration, handling and infrastructure (AHI) fee:**", "+ $0.00")
    st.write("**+ Dispensing fee:**", "+ $0.00")

    st.markdown("---")
    st.write("**DPMQ:**", "**$0.00**")

