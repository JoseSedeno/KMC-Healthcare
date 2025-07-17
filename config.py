from decimal import Decimal

PBS_CONSTANTS = {
    "DISPENSING_FEE": Decimal("8.67"),
    "AHI_BASE": Decimal("4.79"),
    "AHI_CAP": Decimal("99.79"),
    "DANGEROUS_FEE": Decimal("5.37"),

    "WHOLESALE_MARKUP_RATE": Decimal("0.0752"),
    "WHOLESALE_FLAT_FEE": Decimal("54.14"),

    "WHOLESALE_TIER_THRESHOLDS": {
        "TIER1": Decimal("19.37"),
        "TIER2": Decimal("821.31")
    },

    "WHOLESALE_FIXED_FEE_TIER1": Decimal("0.41"),

    "AHI_BREAKPOINT_LOW": Decimal("100.00"),
    "AHI_BREAKPOINT_HIGH": Decimal("2000.00"),
    "AHI_TIER2_RATE": Decimal("0.05")
}
