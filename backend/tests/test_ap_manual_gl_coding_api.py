"""
Manual GL coding and coding-rule API tests.

These exercise the real FastAPI routes against a small fake database. Payment
providers are not involved, which keeps the manual AP path independently
testable.
"""

from uuid import uuid4


def _account(org_id, account_id, code="1200", name="Test Inventory", postable=True):
    return {
        "id": str(account_id),
        "org_id": str(org_id),
        "account_code": code,
        "account_name": name,
        "account_type": "asset",
        "is_active": True,
        "is_postable": postable,
    }


def test_save_line_coding_new(ap_api):
    org_id = ap_api.org_id
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()
    ap_api.db.seed("chart_of_accounts", _account(org_id, gl_account_id))

    response = ap_api.client.put(
        f"/api/v2/ap/codings/{document_id}/line/{line_item_id}",
        json={"gl_account_id": str(gl_account_id), "amount": 150.00},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["gl_account"]["id"] == str(gl_account_id)
    assert data["gl_account"]["account_code"] == "1200"
    stored = ap_api.db.tables["invoice_codings"]
    assert len(stored) == 1
    assert stored[0]["source"] == "manual"
    assert stored[0]["status"] == "approved"
    assert stored[0]["line_item_id"] == str(line_item_id)


def test_save_line_coding_update_existing(ap_api):
    org_id = ap_api.org_id
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id_1 = uuid4()
    gl_account_id_2 = uuid4()
    ap_api.db.seed(
        "chart_of_accounts",
        _account(org_id, gl_account_id_1, code="1200"),
        _account(org_id, gl_account_id_2, code="1210"),
    )
    ap_api.db.seed(
        "invoice_codings",
        {
            "id": "coding-1",
            "org_id": str(org_id),
            "document_id": str(document_id),
            "line_item_id": str(line_item_id),
            "amount": 100,
        },
    )

    response = ap_api.client.put(
        f"/api/v2/ap/codings/{document_id}/line/{line_item_id}",
        json={"gl_account_id": str(gl_account_id_2), "amount": 200.00},
    )

    assert response.status_code == 200
    assert response.json()["gl_account"]["account_code"] == "1210"
    stored = ap_api.db.tables["invoice_codings"]
    assert len(stored) == 1
    assert stored[0]["gl_account_code"] == "1210"
    assert float(stored[0]["amount"]) == 200.0


def test_save_line_coding_non_postable_account(ap_api):
    org_id = ap_api.org_id
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()
    ap_api.db.seed(
        "chart_of_accounts",
        _account(org_id, gl_account_id, code="9900", name="Non-Postable", postable=False),
    )

    response = ap_api.client.put(
        f"/api/v2/ap/codings/{document_id}/line/{line_item_id}",
        json={"gl_account_id": str(gl_account_id), "amount": 100.00},
    )

    assert response.status_code == 409
    assert "not postable" in response.json()["detail"]["message"]


def test_save_line_coding_account_not_found(ap_api):
    response = ap_api.client.put(
        f"/api/v2/ap/codings/{uuid4()}/line/{uuid4()}",
        json={"gl_account_id": str(uuid4()), "amount": 100.00},
    )

    assert response.status_code == 404
    assert "GL account not found" in response.json()["detail"]["message"]


def test_create_coding_rule_basic(ap_api):
    org_id = ap_api.org_id
    gl_account_id = uuid4()
    ap_api.db.seed("chart_of_accounts", _account(org_id, gl_account_id))

    response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Auto-code: Office Supplies",
            "description": "Auto-assign Inventory for office supplies",
            "description_pattern": "Office Supplies",
            "gl_account_id": str(gl_account_id),
            "priority": 100,
        },
    )

    assert response.status_code == 200
    rule = response.json()
    assert rule["name"] == "Auto-code: Office Supplies"
    assert rule["description_pattern"] == "Office Supplies"
    assert rule["gl_account_id"] == str(gl_account_id)
    assert rule["is_active"] is True


def test_create_coding_rule_non_postable_fails(ap_api):
    org_id = ap_api.org_id
    gl_account_id = uuid4()
    ap_api.db.seed(
        "chart_of_accounts",
        _account(org_id, gl_account_id, code="9900", name="Non-Postable", postable=False),
    )

    response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Test Rule",
            "description": "Test rule for non-postable",
            "gl_account_id": str(gl_account_id),
            "priority": 100,
        },
    )

    assert response.status_code == 409
    assert "not postable" in response.json()["detail"]["message"]


def test_list_coding_rules(ap_api):
    org_id = ap_api.org_id
    ap_api.db.seed(
        "coding_rules",
        {
            "id": "rule-2",
            "org_id": str(org_id),
            "name": "Rule 2",
            "priority": 200,
            "is_active": True,
        },
        {
            "id": "rule-1",
            "org_id": str(org_id),
            "name": "Rule 1",
            "priority": 100,
            "is_active": True,
        },
    )

    response = ap_api.client.get("/api/v2/ap/coding-rules")

    assert response.status_code == 200
    rules = response.json()
    assert [rule["name"] for rule in rules] == ["Rule 1", "Rule 2"]
    assert [rule["priority"] for rule in rules] == [100, 200]


def test_save_line_coding_gl_coding_panel_integration(ap_api):
    org_id = ap_api.org_id
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()
    ap_api.db.seed("chart_of_accounts", _account(org_id, gl_account_id))

    save_response = ap_api.client.put(
        f"/api/v2/ap/codings/{document_id}/line/{line_item_id}",
        json={"gl_account_id": str(gl_account_id), "amount": 150.00},
    )
    assert save_response.status_code == 200

    verify_response = ap_api.client.get(f"/api/v2/ap/codings/{document_id}")
    assert verify_response.status_code == 200
    codings = verify_response.json()
    assert len(codings) == 1
    assert codings[0]["source"] == "manual"
    assert codings[0]["status"] == "approved"
    assert codings[0]["confidence"] == 100


def test_approval_rules_configuration_ui_data(ap_api, monkeypatch):
    org_id = ap_api.org_id

    class FakeChartOfAccountsService:
        async def list(self, *_args, **_kwargs):
            return [
                {
                    "id": "gl-1200",
                    "account_code": "1200",
                    "account_name": "Inventory",
                    "is_postable": True,
                    "is_active": True,
                },
                {
                    "id": "gl-4000",
                    "account_code": "4000",
                    "account_name": "Revenue",
                    "is_postable": True,
                    "is_active": True,
                },
            ]

    monkeypatch.setattr(
        "app.routers.ap.ChartOfAccountsService", FakeChartOfAccountsService
    )
    assert org_id is not None

    chart_response = ap_api.client.get(
        "/api/v2/ap/chart-of-accounts", params={"include_inactive": False}
    )
    rules_response = ap_api.client.get("/api/v2/ap/coding-rules")

    assert chart_response.status_code == 200
    assert len(chart_response.json()) == 2
    assert rules_response.status_code == 200
    assert rules_response.json() == []


def test_manual_gl_coding_failure_scenarios(ap_api):
    # Missing required fields fail validation before touching the database.
    response = ap_api.client.put(
        f"/api/v2/ap/codings/{uuid4()}/line/{uuid4()}",
        json={},
    )
    assert response.status_code == 422

    # Invalid UUID path segments are rejected as validation errors.
    response = ap_api.client.put(
        f"/api/v2/ap/codings/{uuid4()}/line/invalid-line-id",
        json={"gl_account_id": str(uuid4()), "amount": 100.00},
    )
    assert response.status_code == 422


def test_coding_rules_configuration_workflow(ap_api):
    org_id = ap_api.org_id
    gl_account_id = uuid4()
    ap_api.db.seed("chart_of_accounts", _account(org_id, gl_account_id))

    first = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Initial Rule",
            "description": "Initial approval rule for testing",
            "gl_account_id": str(gl_account_id),
            "priority": 100,
        },
    )
    assert first.status_code == 200

    second = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Second Rule",
            "description": "Second approval rule for testing",
            "gl_account_id": str(gl_account_id),
            "priority": 200,
        },
    )
    assert second.status_code == 200

    listed = ap_api.client.get("/api/v2/ap/coding-rules")
    assert listed.status_code == 200
    rules = listed.json()
    assert [rule["priority"] for rule in rules] == [100, 200]
    assert [rule["name"] for rule in rules] == ["Initial Rule", "Second Rule"]
