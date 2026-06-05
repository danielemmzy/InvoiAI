import logging
from app.models.invoice import StructuredDocument
 
logger = logging.getLogger(__name__)
 
TOLERANCE = 0.02
 
 
def validate_document(doc: StructuredDocument) -> list[str]:
    warnings = []
 
    if not doc.sections:
        warnings.append("No data could be extracted. Document may be blank or unreadable.")
        return warnings
 
    if doc.extraction_confidence == "low":
        warnings.append("Low extraction confidence — please review results carefully.")
 
    if doc.document_type in ("Unknown", "", None):
        warnings.append("Document type could not be identified.")
 
    warnings.extend(_check_totals(doc.raw_totals))
 
    empty = [n for n, d in doc.sections.items() if not d]
    if empty:
        warnings.append(f"Empty sections detected: {', '.join(empty)}")
 
    if warnings:
        logger.info(f"Validation: {len(warnings)} warning(s)")
    else:
        logger.info("Validation passed cleanly")
 
    return warnings
 
 
def _check_totals(raw_totals: dict) -> list[str]:
    if not raw_totals or len(raw_totals) < 2:
        return []
 
    totals = {
        k.lower().replace(" ", "_"): v
        for k, v in raw_totals.items()
        if isinstance(v, (int, float))
    }
 
    total = _find(totals, ["total", "total_amount", "grand_total", "amount_due"])
    subtotal = _find(totals, ["subtotal", "sub_total", "net_amount"])
    tax = _find(totals, ["tax", "tax_amount", "vat", "gst"])
    shipping = _find(totals, ["shipping", "shipping_cost", "freight"])
 
    if total and subtotal and tax:
        expected = subtotal + tax + (shipping or 0)
        if abs(expected - total) > TOLERANCE:
            return [
                f"Totals mismatch: subtotal + tax = {expected:.2f} "
                f"but document total is {total:.2f}"
            ]
    return []
 
 
def _find(totals: dict, candidates: list[str]):
    for c in candidates:
        if c in totals:
            return totals[c]
    return None