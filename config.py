from decimal import Decimal

PBS_CONSTANTS = {
    # 💊 Dispensing & Handling Fees
    "DISPENSING_FEE": Decimal("8.67"),
    "DANGEROUS_FEE": Decimal("5.37"),

    # 📦 AHI Fee Structure
    "AHI_BASE": Decimal("4.79"),
    "AHI_TIER1_CAP": Decimal("100.00"),
    "AHI_TIER2_CAP": Decimal("2000.00"),
    "AHI_MAX_FEE": Decimal("99.79"),

    # 🏷️ Wholesale Markup Structure
    "WHOLESALE_FIXED_FEE_TIER1": Decimal("0.41"),
    "WHOLESALE_MARKUP_RATE": Decimal("0.0752"),
    "WHOLESALE_FLAT_FEE": Decimal("54.14"),

    # 🔢 Threshold for switching from Tier 1 fixed to Tier 2 percentage
    "WHOLESALE_AEMP_THRESHOLD": Decimal("5.50"),

    # 🧮 Wholesale Tier Thresholds based on DPMQ
    "WHOLESALE_TIER_THRESHOLDS": {
        "TIER1": Decimal("19.37"),
        "TIER2": Decimal("821.31")
    },

    # 📈 Max AEMP for Tier 2 before Tier 3 flat fee applies
    "WHOLESALE_TIER2_CAP": Decimal("720.00"),

    # 🏥 Section 100 – Efficient Funding of Chemotherapy (EFC)
    "EFC_AHI_PUBLIC": Decimal("90.13"),
    "EFC_AHI_PRIVATE": Decimal("134.80"),
    "EFC_PRIVATE_MARKUP_RATE": Decimal("0.014"),
    "EFC_PRIVATE_MARKUP_MULTIPLIER": Decimal("1.014"),
}
