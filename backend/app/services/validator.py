import logging
from app.models.invoice import StructuredDocument

logger = logging.getLogger(__name__)

TOLERANCE = 0.02  # 2 cents rounding tolerance


def validate_document(doc: StructuredDocument) -> list[str]:
    """
    Industry-agnostic validation.

    Since GPT decides the fields, we can't validate specific field names.
    Instead we validate things we always know:
      1. Was anything extracted at all?
      2. Do monetary totals add up (using raw_totals)?
      3. Is confidence low? (warn the user to double-check)

    Returns list of human-readable warnings shown to the user.
    Warnings never block — document is always saved and returned.
    """
    warnings = []

    # ── 1. Empty extraction check ─────────────────────────────────────────────
    if not doc.sections:
        warnings.append(
            "No structured data could be extracted. "
            "The document may be corrupted, blank, or unreadable."
        )
        return warnings  # no point running further checks

    # ── 2. Low confidence warning ─────────────────────────────────────────────
    if doc.extraction_confidence == "low":
        warnings.append(
            "Extraction confidence is low. "
            "Please review the results carefully before using them."
        )

    # ── 3. Document type unknown ──────────────────────────────────────────────
    if doc.document_type in ("Unknown", "", None):
        warnings.append(
            "Document type could not be identified. "
            "Results may be incomplete."
        )

    # ── 4. Totals cross-check ─────────────────────────────────────────────────
    # We use raw_totals which GPT always fills regardless of industry.
    # Check if any two totals that should match actually match.
    totals_warnings = _check_totals(doc.raw_totals)
    warnings.extend(totals_warnings)

    # ── 5. Empty sections check ───────────────────────────────────────────────
    empty_sections = [
        name for name, data in doc.sections.items()
        if data is None or data == {} or data == []
    ]
    if empty_sections:
        warnings.append(
            f"These sections appear empty: {', '.join(empty_sections)}"
        )

    if warnings:
        logger.info(f"Validation produced {len(warnings)} warning(s)")
    else:
        logger.info("Validation passed cleanly")

    return warnings


def _check_totals(raw_totals: dict) -> list[str]:
    """
    Looks for common total mismatches in raw_totals.

    Common patterns across industries:
      subtotal + tax = total
      subtotal + tax + shipping = total
      sum of line totals ≈ subtotal or total

    We check loosely — we only warn if we find clear named pairs.
    We never assume field names that might not exist.
    """
    warnings = []

    if not raw_totals or len(raw_totals) < 2:
        return warnings

    # Normalize keys to lowercase for matching
    totals = {k.lower().replace(" ", "_"): v
              for k, v in raw_totals.items()
              if isinstance(v, (int, float))}

    total = _find_key(totals, ["total", "total_amount", "grand_total", "amount_due", "invoice_total"])
    subtotal = _find_key(totals, ["subtotal", "sub_total", "net_amount", "net_total"])
    tax = _find_key(totals, ["tax", "tax_amount", "vat", "gst", "sales_tax"])
    shipping = _find_key(totals, ["shipping", "shipping_cost", "freight", "delivery"])

    # Check subtotal + tax = total
    if total and subtotal and tax:
        expected = subtotal + tax + (shipping or 0)
        if abs(expected - total) > TOLERANCE:
            warnings.append(
                f"Totals mismatch: subtotal ({subtotal}) + tax ({tax}) "
                f"= {expected:.2f} but total is {total:.2f}"
            )

    return warnings


def _find_key(totals: dict, candidates: list[str]):
    """
    Returns the first matching value from a list of candidate key names.
    Used to find totals regardless of exact naming (total vs total_amount vs grand_total).
    """
    for candidate in candidates:
        if candidate in totals:
            return totals[candidate]
    return None