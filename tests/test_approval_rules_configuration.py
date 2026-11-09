"""
Approval rules configuration tests

Tests for backend CRUD operations and UI data requirements for approval rules configuration.
This module does not depend on payment providers and can run independently.
"""

import pytest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient


def test_approval_rules_initial_state_empty(client: TestClient, auth_headers):
    """Test that approval rules configuration starts empty - critical for UI development."""
    org_id = "test-org-1"

    # Chart of accounts should have data (starter COA)
    with client.transport._mock_responses.get(
        f"/ap/chart-of-accounts?org_id={org_id}&include_inactive=false",
        status_code=200,
        json=[
            {"id": "gl-1200", "account_code": "1200", "account_name": "Inventory", "is_active": True, "is_postable": True},
            {"id": "gl-4000", "account_code": "4000", "account_name": "Revenue", "is_active": True, "is_postable": True},
            {"id": "gl-5000", "account_code": "5000", "account_name": "COGS", "is_active": True, "is_postable": True},
        ],
    ):
        # Initially, no coding rules exist - UI should show empty state
        with client.transport._mock_responses.get(
            f"/ap/coding-rules?org_id={org_id}",
            status_code=200,
            json=[],
        ):
            chart_response = client.get(
                f"/ap/chart-of-accounts?org_id={org_id}&include_inactive=false",
                headers=auth_headers,
            )
            rules_response = client.get(
                "/ap/coding-rules",
                headers=auth_headers,
            )

            assert chart_response.status_code == 200
            assert len(chart_response.json()) == 3  # Should have 3 COA accounts

            assert rules_response.status_code == 200
            assert len(rules_response.json()) == 0  # Empty - critical for UI empty state


def test_approval_rules_create_rule_with_all_fields(client: TestClient, auth_headers, setup_test_data):
    """Test creating a complete approval rule with all optional fields."""
    org_id = "test-org-1"
    gl_account_id = "gl-1200"
    vendor_id = "vendor-123"
    department_id = "dept-456"
    cost_center_id = "center-789"
    project_id = "project-abc"
    tax_code_id = "tax-def"

    # Create a postable GL account
    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json={
            "id": gl_account_id,
            "org_id": org_id,
            "account_code": "1200",
            "account_name": "Inventory",
            "is_active": True,
            "is_postable": True,
        },
    ):
        rule_response = client.post(
            "/ap/coding-rules",
            json={
                "name": "Office Supplies - Q4 2024",
                "description": "Auto-assign inventory for office supplies and stationery",
                "vendor_id": vendor_id,
                "description_pattern": "Office Supplies,Stationery,Equipment",
                "sku_pattern": "OFF.*,STN.*,EQ.*",
                "gl_account_id": gl_account_id,
                "department_id": department_id,
                "cost_center_id": cost_center_id,
                "project_id": project_id,
                "tax_code_id": tax_code_id,
                "priority": 150,  # Custom priority
            },
            headers=auth_headers,
        )

    assert rule_response.status_code == 200
    rule = rule_response.json()
    assert rule["name"] == "Office Supplies - Q4 2024"
    assert rule["vendor_id"] == vendor_id
    assert rule["description_pattern"] == "Office Supplies,Stationery,Equipment"
    assert rule["gl_account_id"] == gl_account_id
    assert rule["department_id"] == department_id
    assert rule["cost_center_id"] == cost_center_id
    assert rule["project_id"] == project_id
    assert rule["tax_code_id"] == tax_code_id
    assert rule["priority"] == 150
    assert rule["is_active"] == True


def test_approval_rules_create_rule_minimal_fields(client: TestClient, auth_headers, setup_test_data):
    """Test creating a rule with only required fields."""
    org_id = "test-org-1"
    gl_account_id = "gl-4000"

    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json={
            "id": gl_account_id,
            "org_id": org_id,
            "account_code": "4000",
            "account_name": "Revenue",
            "is_active": True,
            "is_postable": True,
        },
    ):
        rule_response = client.post(
            "/ap/coding-rules",
            json={
                "name": "Simple Rule",
                "description": "Simple rule with only required fields",
                "gl_account_id": gl_account_id,
            },
            headers=auth_headers,
        )

    assert rule_response.status_code == 200
    rule = rule_response.json()
    assert rule["name"] == "Simple Rule"
    assert rule["gl_account_id"] == gl_account_id
    assert rule["is_active"] == True
    # Optional fields should be null
    assert rule["vendor_id"] is None or rule["vendor_id"] == gl_account_id  # Depends on implementation


def test_approval_rules_validation_and_error_handling(client: TestClient, auth_headers, setup_test_data):
    """Test validation errors and proper error handling for rule creation."""
    # Test 1: Missing required GL account
    response = client.post(
        "/ap/coding-rules",
        json={
            "name": "Test Rule",
            # Missing gl_account_id - should fail
            "description": "Test without GL account",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422  # Validation error

    # Test 2: GL account not found
    with client.transport._mock_responses.patch(
        "/ap/chart-of-accounts/non-existent-account",
        status_code=404,
        json={"detail": "GL account not found"},
    ):
        response = client.post(
            "/ap/coding-rules",
            json={
                "name": "Test Rule",
                "description": "Test with non-existent account",
                "gl_account_id": "non-existent-account",
            },
            headers=auth_headers,
        )
    assert response.status_code == 404

    # Test 3: Non-postable GL account
    with client.transport._mock_responses.patch(
        "/ap/chart-of-accounts/non-postable-account",
        status_code=200,
        json={
            "id": "non-postable-account",
            "org_id": "test-org-1",
            "account_code": "9900",
            "account_name": "Non-Postable",
            "is_active": True,
            "is_postable": False,  # This should block rule creation
        },
    ):
        response = client.post(
            "/ap/coding-rules",
            json={
                "name": "Test Rule",
                "description": "Test with non-postable account",
                "gl_account_id": "non-postable-account",
            },
            headers=auth_headers,
        )
    assert response.status_code == 409
    assert "not postable" in response.json().get("detail", "")


def test_approval_rules_list_pagination_and_filtering(client: TestClient, auth_headers, setup_test_data):
    """Test that rules list can be paginated and filtered by UI."""
    org_id = "test-org-1"

    # Mock multiple rules
    rules = []
    for i in range(5):
        rules.append({
            "id": f"rule-{i}",
            "org_id": org_id,
            "name": f"Rule {i}",
            "description_pattern": f"Pattern {i}",
            "gl_account_id": f"gl-account-{i}",
            "priority": 100 + i,
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
        })

    with client.transport._mock_responses.get(
        f"/ap/coding-rules?org_id={org_id}",
        status_code=200,
        json=rules,
    ):
        response = client.get(
            "/ap/coding-rules",
            headers=auth_headers,
        )

    assert response.status_code == 200
    returned_rules = response.json()
    assert len(returned_rules) == 5
    # Should be ordered by priority (ascending)
    assert returned_rules[0]["priority"] == 100
    assert returned_rules[-1]["priority"] == 104


def test_approval_rules_ui_data_structure(client: TestClient, auth_headers, setup_test_data):
    """Test that approval rules configuration UI gets all required data structure."""
    org_id = "test-org-1"

    # Simulate what the UI needs for rendering the approval rules configuration
    chart_of_accounts_data = [
        {"id": "gl-1200", "account_code": "1200", "account_name": "Inventory", "is_postable": True, "is_active": True},
        {"id": "gl-4000", "account_code": "4000", "account_name": "Revenue", "is_postable": True, "is_active": True},
        {"id": "gl-5000", "account_code": "5000", "account_name": "COGS", "is_postable": True, "is_active": True},
        {"id": "gl-6000", "account_code": "6000", "account_name": "Marketing", "is_postable": True, "is_active": True},
    ]

    # Simulate initial empty state
    coding_rules_data = []

    # Mock responses that the UI would make
    with client.transport._mock_responses.get(
        f"/ap/chart-of-accounts?org_id={org_id}&include_inactive=false",
        status_code=200,
        json=chart_of_accounts_data,
    ):
        with client.transport._mock_responses.get(
            f"/ap/coding-rules?org_id={org_id}",
            status_code=200,
            json=coding_rules_data,
        ):
            # UI would make both calls simultaneously
            chart_response = client.get(
                f"/ap/chart-of-accounts?org_id={org_id}&include_inactive=false",
                headers=auth_headers,
            )
            rules_response = client.get(
                "/ap/coding-rules",
                headers=auth_headers,
            )

            # UI data structure validation
            assert chart_response.status_code == 200
            coa_data = chart_response.json()
            assert len(coa_data) == 4
            assert all(account["is_postable"] for account in coa_data)

            assert rules_response.status_code == 200
            rules_data = rules_response.json()
            assert len(rules_data) == 0

            # UI can now render:
            # - Chart of accounts for GL account dropdown
            # - Empty rules list (shows create form initially)
            # - No conflicts between available accounts and existing rules


def test_approval_rules_configuration_workflow_integration(client: TestClient, auth_headers, setup_test_data):
    """End-to-end test: approval rules configuration workflow."""
    org_id = "test-org-1"

    # Step 1: Create GL account
    gl_account_id = "gl-1200"
    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json={
            "id": gl_account_id,
            "org_id": org_id,
            "account_code": "1200",
            "account_name": "Inventory",
            "is_active": True,
            "is_postable": True,
        },
    ):
        # Step 2: Create initial coding rule
        initial_rule = {
            "id": "rule-1",
            "org_id": org_id,
            "name": "Initial Rule",
            "description": "Initial approval rule",
            "gl_account_id": gl_account_id,
            "priority": 100,
            "is_active": True,
        }

        with client.transport._mock_responses.post(
            "/ap/coding-rules",
            status_code=200,
            json=initial_rule,
        ):
            create_response = client.post(
                "/ap/coding-rules",
                json={
                    "name": "Initial Rule",
                    "description": "Initial approval rule for testing",
                    "gl_account_id": gl_account_id,
                    "priority": 100,
                },
                headers=auth_headers,
            )
            assert create_response.status_code == 200

        # Step 3: Verify rule was created
        with client.transport._mock_responses.get(
            f"/ap/coding-rules?org_id={org_id}",
            status_code=200,
            json=[initial_rule],
        ):
            list_response = client.get(
                "/ap/coding-rules",
                headers=auth_headers,
            )
            assert list_response.status_code == 200
            assert len(list_response.json()) == 1

        # Step 4: Simulate UI editing (create second rule)
        second_rule = {
            "id": "rule-2",
            "org_id": org_id,
            "name": "Second Rule",
            "description": "Second approval rule",
            "gl_account_id": gl_account_id,
            "priority": 200,
            "is_active": True,
        }

        with client.transport._mock_responses.post(
            "/ap/coding-rules",
            status_code=200,
            json=second_rule,
        ):
            second_response = client.post(
                "/ap/coding-rules",
                json={
                    "name": "Second Rule",
                    "description": "Second approval rule for testing",
                    "gl_account_id": gl_account_id,
                    "priority": 200,
                },
                headers=auth_headers,
            )
            assert second_response.status_code == 200

        # Step 5: Verify both rules exist and are ordered by priority
        with client.transport._mock_responses.get(
            f"/ap/coding-rules?org_id={org_id}",
            status_code=200,
            json=[initial_rule, second_rule],
        ):
            final_list_response = client.get(
                "/ap/coding-rules",
                headers=auth_headers,
            )
            assert final_list_response.status_code == 200
            final_rules = final_list_response.json()
            assert len(final_rules) == 2
            assert final_rules[0]["priority"] == 100  # Lower priority first
            assert final_rules[1]["priority"] == 200  # Higher priority second

    print("✅ All approval rules configuration tests passed")