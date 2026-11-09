"""Approval routing must not select columns the documents table does not have."""

from app.services.ap.approval_bridge import document_routing_dimensions


def test_capture_overrides_win_over_external_payload():
    doc = {
        "capture_overrides": {"department": "Warehouse", "cost_center": "CC-2"},
        "external_source_data": {
            "department": "Sales",
            "location": "Chicago",
        },
    }

    assert document_routing_dimensions(doc) == ("Warehouse", "CC-2", "Chicago")


def test_missing_payloads_are_treated_as_empty():
    assert document_routing_dimensions({}) == (None, None, None)
    assert document_routing_dimensions({"capture_overrides": None}) == (
        None,
        None,
        None,
    )


def test_blank_values_do_not_match_a_rule():
    doc = {"external_source_data": {"department": "", "cost_center": "  "}}

    assert document_routing_dimensions(doc) == (None, None, None)
