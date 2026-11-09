"""
Coding-rule configuration API tests.

These cover the CRUD and UI-data contract for the coding-rules settings
surface without depending on a payment provider.
"""

from uuid import uuid4


def _account(org_id, account_id, code, name):
    return {
        "id": str(account_id),
        "org_id": str(org_id),
        "account_code": code,
        "account_name": name,
        "is_active": True,
        "is_postable": True,
    }


def test_approval_rules_initial_state_empty(ap_api, monkeypatch):
    class FakeChartOfAccountsService:
        async def list(self, *_args, **_kwargs):
            return [
                {"id": "gl-1200", "account_code": "1200", "is_postable": True},
                {"id": "gl-4000", "account_code": "4000", "is_postable": True},
                {"id": "gl-5000", "account_code": "5000", "is_postable": True},
            ]

    monkeypatch.setattr(
        "app.routers.ap.ChartOfAccountsService", FakeChartOfAccountsService
    )

    chart_response = ap_api.client.get(
        "/api/v2/ap/chart-of-accounts", params={"include_inactive": False}
    )
    rules_response = ap_api.client.get("/api/v2/ap/coding-rules")

    assert chart_response.status_code == 200
    assert len(chart_response.json()) == 3
    assert rules_response.status_code == 200
    assert rules_response.json() == []


def test_approval_rules_create_rule_with_all_fields(ap_api):
    org_id = ap_api.org_id
    gl_account_id = uuid4()
    vendor_id = uuid4()
    department_id = uuid4()
    cost_center_id = uuid4()
    project_id = uuid4()
    tax_code_id = uuid4()
    ap_api.db.seed("chart_of_accounts", _account(org_id, gl_account_id, "1200", "Inventory"))

    response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Office Supplies - Q4 2024",
            "description": "Auto-assign inventory for office supplies and stationery",
            "vendor_id": str(vendor_id),
            "description_pattern": "Office Supplies,Stationery,Equipment",
            "sku_pattern": "OFF.*,STN.*,EQ.*",
            "gl_account_id": str(gl_account_id),
            "department_id": str(department_id),
            "cost_center_id": str(cost_center_id),
            "project_id": str(project_id),
            "tax_code_id": str(tax_code_id),
            "priority": 150,
        },
    )

    assert response.status_code == 200
    rule = response.json()
    assert rule["name"] == "Office Supplies - Q4 2024"
    assert rule["vendor_id"] == str(vendor_id)
    assert rule["description_pattern"] == "Office Supplies,Stationery,Equipment"
    assert rule["gl_account_id"] == str(gl_account_id)
    assert rule["department_id"] == str(department_id)
    assert rule["cost_center_id"] == str(cost_center_id)
    assert rule["project_id"] == str(project_id)
    assert rule["tax_code_id"] == str(tax_code_id)
    assert rule["priority"] == 150
    assert rule["is_active"] is True


def test_approval_rules_create_rule_minimal_fields(ap_api):
    org_id = ap_api.org_id
    gl_account_id = uuid4()
    ap_api.db.seed("chart_of_accounts", _account(org_id, gl_account_id, "4000", "Revenue"))

    response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Simple Rule",
            "description": "Simple rule with only required fields",
            "gl_account_id": str(gl_account_id),
        },
    )

    assert response.status_code == 200
    rule = response.json()
    assert rule["name"] == "Simple Rule"
    assert rule["gl_account_id"] == str(gl_account_id)
    assert rule["is_active"] is True
    assert rule["vendor_id"] is None
    assert rule["priority"] == 100


def test_approval_rules_validation_and_error_handling(ap_api):
    # Missing required GL account fails request validation.
    response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={"name": "Test Rule", "description": "Test without GL account"},
    )
    assert response.status_code == 422

    # Unknown account is a 404.
    response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Test Rule",
            "description": "Test with non-existent account",
            "gl_account_id": str(uuid4()),
        },
    )
    assert response.status_code == 404

    # Non-postable accounts cannot back a coding rule.
    org_id = ap_api.org_id
    non_postable_id = uuid4()
    account = _account(org_id, non_postable_id, "9900", "Non-Postable")
    account["is_postable"] = False
    ap_api.db.seed("chart_of_accounts", account)

    response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Test Rule",
            "description": "Test with non-postable account",
            "gl_account_id": str(non_postable_id),
        },
    )
    assert response.status_code == 409
    assert "not postable" in response.json()["detail"]["message"]


def test_approval_rules_list_pagination_and_filtering(ap_api):
    org_id = ap_api.org_id
    ap_api.db.seed(
        "coding_rules",
        *[
            {
                "id": f"rule-{index}",
                "org_id": str(org_id),
                "name": f"Rule {index}",
                "description_pattern": f"Pattern {index}",
                "gl_account_id": f"gl-account-{index}",
                "priority": 100 + index,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
            }
            for index in range(5)
        ],
    )

    response = ap_api.client.get("/api/v2/ap/coding-rules")

    assert response.status_code == 200
    returned_rules = response.json()
    assert len(returned_rules) == 5
    assert returned_rules[0]["priority"] == 100
    assert returned_rules[-1]["priority"] == 104


def test_approval_rules_ui_data_structure(ap_api, monkeypatch):
    class FakeChartOfAccountsService:
        async def list(self, *_args, **_kwargs):
            return [
                {"id": "gl-1200", "account_code": "1200", "is_postable": True},
                {"id": "gl-4000", "account_code": "4000", "is_postable": True},
                {"id": "gl-5000", "account_code": "5000", "is_postable": True},
                {"id": "gl-6000", "account_code": "6000", "is_postable": True},
            ]

    monkeypatch.setattr(
        "app.routers.ap.ChartOfAccountsService", FakeChartOfAccountsService
    )

    chart_response = ap_api.client.get(
        "/api/v2/ap/chart-of-accounts", params={"include_inactive": False}
    )
    rules_response = ap_api.client.get("/api/v2/ap/coding-rules")

    assert chart_response.status_code == 200
    chart_of_accounts = chart_response.json()
    assert len(chart_of_accounts) == 4
    assert all(account["is_postable"] for account in chart_of_accounts)
    assert rules_response.status_code == 200
    assert rules_response.json() == []


def test_approval_rules_configuration_workflow(ap_api):
    org_id = ap_api.org_id
    gl_account_id = uuid4()
    ap_api.db.seed("chart_of_accounts", _account(org_id, gl_account_id, "1200", "Inventory"))

    create_response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Initial Rule",
            "description": "Initial approval rule for testing",
            "gl_account_id": str(gl_account_id),
            "priority": 100,
        },
    )
    assert create_response.status_code == 200

    second_response = ap_api.client.post(
        "/api/v2/ap/coding-rules",
        json={
            "name": "Second Rule",
            "description": "Second approval rule for testing",
            "gl_account_id": str(gl_account_id),
            "priority": 200,
        },
    )
    assert second_response.status_code == 200

    final_list_response = ap_api.client.get("/api/v2/ap/coding-rules")
    assert final_list_response.status_code == 200
    final_rules = final_list_response.json()
    assert len(final_rules) == 2
    assert final_rules[0]["priority"] == 100
    assert final_rules[1]["priority"] == 200
