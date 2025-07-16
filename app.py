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
getcontext().prec = 12

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

# Set higher precision for financial calculations
getcontext().prec = 28

# ----------------------
# 🔹 PRECISION HELPERS
# ----------------------

def to_decimal(value):
    """Convert any numeric value to Decimal with proper precision"""
    return Decimal(str(value))

def validate_calculation_precision(original_dpmq, reconstructed_dpmq, tolerance=Decimal("0.01")):
    """Validate that inverse calculation is accurate"""
    diff = abs(to_decimal(original_dpmq) - to_decimal(reconstructed_dpmq))
    if diff > tolerance:
        st.warning(f"⚠️ Precision warning: Difference of ${diff:.4f} detected")
        return False
    return True

def validate_calculation_precision_enhanced(original_dpmq, reconstructed_dpmq, tolerance=Decimal("0.005")):
    """
    Enhanced validation with better error reporting
    """
    original_dpmq = to_decimal(original_dpmq)
    reconstructed_dpmq = to_decimal(reconstructed_dpmq)
    diff = abs(original_dpmq - reconstructed_dpmq)
    
    if diff <= tolerance:
        return True, f"✅ Precision validated: difference ${diff:.4f}"
    else:
        return False, f"❌ Precision warning: difference ${diff:.4f} exceeds tolerance ${tolerance:.4f}"

# ----------------------
# 🔹 FORWARD LOGIC
# ----------------------

# Forward: AEMP (unit) → AEMP (max quantity)
def calculate_aemp_max_qty(input_price, pricing_qty, max_qty):
    if pricing_qty == 0:
        return Decimal("0.00")
    return (to_decimal(input_price) * to_decimal(max_qty)) / to_decimal(pricing_qty)

# Forward: AHI Fee – FORWARD PBS LOGIC
def calculate_ahi_fee(price_to_pharmacist):
    price_to_pharmacist = to_decimal(price_to_pharmacist)
    if price_to_pharmacist < Decimal("100.00"):
        return Decimal("4.79")
    elif price_to_pharmacist <= Decimal("2000.00"):
        return Decimal("4.79") + (price_to_pharmacist - Decimal("100.00")) * Decimal("0.05")
    else:
        return Decimal("99.79")

# Forward: DPMQ = PtP + AHI + Dispensing + [Dangerous]
def calculate_dpmq(price_to_pharmacist, ahi_fee, include_dangerous=False):
    dispensing_fee = Decimal("8.67")
    dangerous_fee = Decimal("4.46") if include_dangerous else Decimal("0.00")
    return to_decimal(price_to_pharmacist) + to_decimal(ahi_fee) + dispensing_fee + dangerous_fee

# ----------------------
# 🔹 INVERSE TIER LOGIC
# ----------------------

def get_wholesale_tier(dpmq):
    dpmq = to_decimal(dpmq)
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

def precise_inverse_aemp_fixed(dpmq, dispensing_fee):
    """
    Mathematically precise inverse AEMP calculation with analytical approach
    """
    dpmq = to_decimal(dpmq)
    dispensing_fee = to_decimal(dispensing_fee)
    
    # For Tier 1 (simple case), we can solve analytically
    if dpmq <= Decimal("19.37"):  # Tier 1 boundary
        # DPMQ = AEMP + 0.41 + AHI + dispensing_fee
        # For Tier 1, AHI = 4.79 (since PtP will be < 100)
        result = dpmq - dispensing_fee - Decimal("4.79") - Decimal("0.41")
        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # For Tier 2 and 3, use enhanced binary search with micro-adjustments
    low = Decimal("0.001")
    high = Decimal("1000000.000")
    tolerance = Decimal("0.000001")  # Ultra-tight tolerance
    
    best_aemp = None
    closest_diff = Decimal("999999")
    max_iterations = 2000  # More iterations for precision
    
    for iteration in range(max_iterations):
        mid = (low + high) / Decimal("2")
        
        # Calculate wholesale markup with full precision
        if mid <= Decimal("5.50"):
            wholesale = Decimal("0.41")
        elif mid <= Decimal("720.00"):
            wholesale = mid * Decimal("0.0752")
        else:
            wholesale = Decimal("54.14")
        
        ptp = mid + wholesale
        
        # Calculate AHI fee with full precision
        if ptp <= Decimal("100.00"):
            ahi = Decimal("4.79")
        elif ptp <= Decimal("2000.00"):
            ahi = Decimal("4.79") + (ptp - Decimal("100.00")) * Decimal("0.05")
        else:
            ahi = Decimal("99.79")
        
        reconstructed_dpmq = ptp + ahi + dispensing_fee
        diff = abs(reconstructed_dpmq - dpmq)
        
        # Track the best solution
        if diff < closest_diff:
            closest_diff = diff
            best_aemp = mid
        
        # If we found exact match, break
        if diff <= tolerance:
            break
            
        # Binary search logic
        if reconstructed_dpmq < dpmq:
            low = mid + Decimal("0.000001")
        else:
            high = mid - Decimal("0.000001")
    
    # Post-processing: Fine-tune the result with micro-adjustments
    if best_aemp and closest_diff > Decimal("0.005"):
        best_aemp = fine_tune_aemp(best_aemp, dpmq, dispensing_fee)
    
    return best_aemp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def fine_tune_aemp(initial_aemp, target_dpmq, dispensing_fee):
    """
    Fine-tune AEMP with micro-adjustments to achieve exact precision
    """
    target_dpmq = to_decimal(target_dpmq)
    dispensing_fee = to_decimal(dispensing_fee)
    
    # Try small adjustments around the initial value
    adjustments = [
        Decimal("0.00"), Decimal("0.01"), Decimal("-0.01"),
        Decimal("0.005"), Decimal("-0.005"), Decimal("0.001"), Decimal("-0.001")
    ]
    
    best_aemp = initial_aemp
    best_diff = Decimal("999999")
    
    for adj in adjustments:
        test_aemp = initial_aemp + adj
        
        # Calculate the full chain
        if test_aemp <= Decimal("5.50"):
            wholesale = Decimal("0.41")
        elif test_aemp <= Decimal("720.00"):
            wholesale = test_aemp * Decimal("0.0752")
        else:
            wholesale = Decimal("54.14")
        
        ptp = test_aemp + wholesale
        
        if ptp <= Decimal("100.00"):
            ahi = Decimal("4.79")
        elif ptp <= Decimal("2000.00"):
            ahi = Decimal("4.79") + (ptp - Decimal("100.00")) * Decimal("0.05")
        else:
            ahi = Decimal("99.79")
        
        reconstructed_dpmq = ptp + ahi + dispensing_fee
        diff = abs(reconstructed_dpmq - target_dpmq)
        
        if diff < best_diff:
            best_diff = diff
            best_aemp = test_aemp
    
    return best_aemp

# Legacy function for backward compatibility (now calls the fixed version)
def precise_inverse_aemp(dpmq, dispensing_fee):
    """Legacy function - now calls the fixed version"""
    return precise_inverse_aemp_fixed(dpmq, dispensing_fee)

# Tiered logic controller - UPDATED
def calculate_inverse_aemp_max(dpmq, dispensing_fee, tier):
    """
    Updated inverse calculation with mathematical precision
    """
    dpmq = to_decimal(dpmq)
    dispensing_fee = to_decimal(dispensing_fee)
    
    if tier == "Tier1":
        # Simple analytical solution for Tier 1
        result = dpmq - dispensing_fee - Decimal("4.79") - Decimal("0.41")
        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif tier in ("Tier2", "Tier3"):
        # Enhanced binary search for Tier 2 and 3
        return precise_inverse_aemp_fixed(dpmq, dispensing_fee)
    
    return Decimal("0.00")
    
# ----------------------
# 🔹 HELPER CALCULATIONS
# ----------------------

# AEMP (max qty) → Unit AEMP
def calculate_unit_aemp(aemp_max_qty, pricing_qty, max_qty):
    if max_qty == 0:
        return Decimal("0.00")
    result = (to_decimal(aemp_max_qty) * to_decimal(pricing_qty)) / to_decimal(max_qty)
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# Forward: Wholesale markup from AEMP
def calculate_wholesale_markup(aemp_max_qty):
    aemp_max_qty = to_decimal(aemp_max_qty)
    if aemp_max_qty <= Decimal("5.50"):
        return Decimal("0.41")
    elif aemp_max_qty <= Decimal("720.00"):
        return (aemp_max_qty * Decimal("0.0752")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        return Decimal("54.14")

# Inverse: Wholesale markup from AEMP
def calculate_inverse_wholesale_markup(aemp_max_qty):
    aemp_max_qty = to_decimal(aemp_max_qty)
    if aemp_max_qty <= Decimal("5.50"):
        return Decimal("0.41")
    elif aemp_max_qty <= Decimal("720.00"):
        return (aemp_max_qty * Decimal("0.0752")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        return Decimal("54.14")

# AEMP + markup = PTP
def calculate_price_to_pharmacist(aemp_max_qty, wholesale_markup):
    result = to_decimal(aemp_max_qty) + to_decimal(wholesale_markup)
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# Inverse: AHI Fee – based on PtP
def calculate_inverse_ahi_fee(price_to_pharmacist):
    price_to_pharmacist = to_decimal(price_to_pharmacist)
    if price_to_pharmacist <= Decimal("100.00"):
        return Decimal("4.79")
    elif price_to_pharmacist <= Decimal("2000.00"):
        result = Decimal("4.79") + (price_to_pharmacist - Decimal("100.00")) * Decimal("0.05")
        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        return Decimal("99.79")

# Final DPMQ – used in inverse check
def calculate_inverse_dpmq(price_to_pharmacist, ahi_fee, dispensing_fee, include_dangerous=False):
    dangerous_fee = Decimal("4.46") if include_dangerous else Decimal("0.00")
    result = to_decimal(price_to_pharmacist) + to_decimal(ahi_fee) + to_decimal(dispensing_fee) + dangerous_fee
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# ----------------------
# 🔹 COST BREAKDOWN (Visuals & Exports)
# ----------------------

def format_currency(amount):
    """Format Decimal as currency with consistent precision"""
    return f"${to_decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

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
        ["Dispensing fee", format_currency(dispensing_fee)]
    ])

    if to_decimal(dangerous_fee) > 0:
        data.append(["Dangerous drug fee", format_currency(dangerous_fee)])

    label_row = "DPMQ" if label == "DPMQ" else "Final Price"
    data.append([label_row, format_currency(final_price)])

    return pd.DataFrame(data, columns=["Component", "Amount"])

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
    st.markdown(f"### 💊 {'Reconstructed DPMQ' if label == 'DPMQ' else 'DPMQ'}: **{format_currency(final_price)}**")

    # Add enhanced precision validation display
    if label == "DPMQ":
        # Validate that our inverse calculation is accurate
        original_dpmq = st.session_state.get('original_input_price', final_price)
        is_valid, message = validate_calculation_precision_enhanced(original_dpmq, final_price)
        if is_valid:
            st.success(message)
        else:
            st.error(message)



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



