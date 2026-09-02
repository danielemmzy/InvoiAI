"""V2 supported industry catalogue."""

SUPPORTED_INDUSTRIES = (
    "general", "retail", "construction", "healthcare", "hospitality",
    "manufacturing", "professional_services", "real_estate", "technology",
    "transportation", "education", "nonprofit",
)
INDUSTRY_LABELS = {value: value.replace("_", " ").title() for value in SUPPORTED_INDUSTRIES}
