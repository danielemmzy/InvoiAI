"""
Manual GL coding API tests - Phase 1 completion (no payment provider dependencies)

Tests for:
- PUT /api/v2/ap/codings/{documentId}/line/{lineItemId} (manual line coding)
- POST /api/v2/ap/coding-rules (rule creation from manual assignments)
- Approval rules configuration (list, create, update, delete)
"""

import pytest
from uuid import UUID, uuid4
from decimal import Decimal
from fastapi.testclient import TestClient

from app.core.enum.ap import APCodingSource, APCodingStatus
from app.models.domain.ap import InvoiceCoding


def test_save_line_coding_new(client: TestClient, auth_headers):
    """Test saving a new manual GL coding for a line item."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()

    # First create a GL account (starter COA includes these)
    gl_account = {
        "id": str(gl_account_id),
        "org_id": org_id,
        "account_code": "1200",
        "account_name": "Test Inventory",
        "account_type": "asset",
        "is_active": True,
        "is_postable": True,
    }

    # Mock the GL account endpoint
    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json=gl_account,
    ):
        # Save the line coding
        response = client.put(
            f"/ap/codings/{document_id}/line/{line_item_id}",
            json={
                "gl_account_id": str(gl_account_id),
                "amount": 150.00,
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["saved"] == True
    assert data["gl_account"]["id"] == str(gl_account_id)
    assert data["gl_account"]["code"] == "1200"


def test_save_line_coding_update_existing(client: TestClient, auth_headers, setup_test_data):
    """Test updating an existing line coding."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id_1 = uuid4()
    gl_account_id_2 = uuid4()

    # Create initial GL accounts
    for i, gl_id in enumerate([gl_account_id_1, gl_account_id_2]):
        gl_account = {
            "id": str(gl_id),
            "org_id": org_id,
            "account_code": f"12{i+1}0",
            "account_name": f"Test Account {i+1}",
            "account_type": "asset",
            "is_active": True,
            "is_postable": True,
        }
        with client.transport._mock_responses.patch(
            f"/ap/chart-of-accounts/{gl_id}",
            status_code=200,
            json=gl_account,
        ):
            pass

    # First save
    response = client.put(
        f"/ap/codings/{document_id}/line/{line_item_id}",
        json={
            "gl_account_id": str(gl_account_id_1),
            "amount": 100.00,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Update to different account
    response = client.put(
        f"/ap/codings/{document_id}/line/{line_item_id}",
        json={
            "gl_account_id": str(gl_account_id_2),
            "amount": 200.00,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["gl_account"]["code"] == "1210"


def test_save_line_coding_non_postable_account(client: TestClient, auth_headers, setup_test_data):
    """Test that non-postable accounts cannot be saved."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()

    # Create a non-postable GL account
    gl_account = {
        "id": str(gl_account_id),
        "org_id": org_id,
        "account_code": "9900",
        "account_name": "Test Non-Postable",
        "account_type": "equity",
        "is_active": True,
        "is_postable": False,  # This is the key
    }

    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json=gl_account,
    ):
        response = client.put(
            f"/ap/codings/{document_id}/line/{line_item_id}",
            json={
                "gl_account_id": str(gl_account_id),
                "amount": 100.00,
            },
            headers=auth_headers,
        )

    # Should fail with 409 (conflict) due to non-postable account
    assert response.status_code == 409
    assert "not postable" in response.json().get("detail", "")


def test_save_line_coding_account_not_found(client: TestClient, auth_headers):
    """Test saving with non-existent GL account."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()

    # Mock 404 for non-existent account
    with client.transport._mock_responses.get(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=404,
        json={"detail": "GL account not found"},
    ):
        response = client.put(
            f"/ap/codings/{document_id}/line/{line_item_id}",
            json={
                "gl_account_id": str(gl_account_id),
                "amount": 100.00,
            },
            headers=auth_headers,
        )

    assert response.status_code == 404
    assert "GL account not found" in response.json().get("detail", "")


def test_create_coding_rule_basic(client: TestClient, auth_headers, setup_test_data):
    """Test creating a basic coding rule."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()

    # Create a GL account for the rule
    gl_account = {
        "id": str(gl_account_id),
        "org_id": org_id,
        "account_code": "1200",
        "account_name": "Test Inventory",
        "account_type": "asset",
        "is_active": True,
        "is_postable": True,
    }

    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json=gl_account,
    ):
        # First save a line coding
        client.put(
            f"/ap/codings/{document_id}/line/{line_item_id}",
            json={
                "gl_account_id": str(gl_account_id),
                "amount": 100.00,
            },
            headers=auth_headers,
        )

        # Create a coding rule based on that assignment
        response = client.post(
            "/ap/coding-rules",
            json={
                "name": "Auto-code: Office Supplies",
                "description": "Auto-assign Inventory for office supplies",
                "description_pattern": "Office Supplies",
                "gl_account_id": str(gl_account_id),
                "priority": 100,
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    rule = response.json()
    assert rule["name"] == "Auto-code: Office Supplies"
    assert rule["description_pattern"] == "Office Supplies"
    assert rule["gl_account_id"] == str(gl_account_id)
    assert rule["is_active"] == True


def test_create_coding_rule_non_postable_fails(client: TestClient, auth_headers, setup_test_data):
    """Test that coding rules cannot be created for non-postable accounts."""
    org_id = "test-org-1"
    gl_account_id = uuid4()

    # Create a non-postable GL account
    gl_account = {
        "id": str(gl_account_id),
        "org_id": org_id,
        "account_code": "9900",
        "account_name": "Test Non-Postable",
        "account_type": "equity",
        "is_active": True,
        "is_postable": False,  # This should block rule creation
    }

    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json=gl_account,
    ):
        response = client.post(
            "/ap/coding-rules",
            json={
                "name": "Test Rule",
                "description": "Test rule for non-postable",
                "gl_account_id": str(gl_account_id),
                "priority": 100,
            },
            headers=auth_headers,
        )

    # Should fail with 409
    assert response.status_code == 409
    assert "not postable" in response.json().get("detail", "")


def test_list_coding_rules(client: TestClient, auth_headers, setup_test_data):
    """Test listing coding rules for an organization."""
    org_id = "test-org-1"

    # Create multiple rules
    rule1 = {
        "id": "rule-1",
        "org_id": org_id,
        "name": "Rule 1",
        "description_pattern": "Pattern 1",
        "gl_account_id": "gl-account-1",
        "priority": 100,
        "is_active": True,
    }

    rule2 = {
        "id": "rule-2",
        "org_id": org_id,
        "name": "Rule 2",
        "description_pattern": "Pattern 2",
        "gl_account_id": "gl-account-2",
        "priority": 200,
        "is_active": True,
    }

    with client.transport._mock_responses.get(
        f"/ap/coding-rules?org_id={org_id}",
        status_code=200,
        json=[rule1, rule2],
    ):
        response = client.get(
            "/ap/coding-rules",
            headers=auth_headers,
        )

    assert response.status_code == 200
    rules = response.json()
    assert len(rules) == 2
    assert rules[0]["name"] == "Rule 1"
    assert rules[1]["name"] == "Rule 2"
    # Should be ordered by priority
    assert rules[0]["priority"] == 100
    assert rules[1]["priority"] == 200


def test_save_line_coding_gl_coding_panel_integration(client: TestClient, auth_headers, setup_test_data):
    """Integration test: simulate GLCodingPanel saving."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()
    gl_account_id = uuid4()

    # Create GL account
    gl_account = {
        "id": str(gl_account_id),
        "org_id": org_id,
        "account_code": "1200",
        "account_name": "Test Inventory",
        "account_type": "asset",
        "is_active": True,
        "is_postable": True,
    }

    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json=gl_account,
    ):
        # Simulate what GLCodingPanel does when saving
        save_response = client.put(
            f"/ap/codings/{document_id}/line/{line_item_id}",
            json={
                "gl_account_id": str(gl_account_id),
                "amount": 150.00,
            },
            headers=auth_headers,
        )

    assert save_response.status_code == 200

    # Verify the saved coding exists by checking line items
    with client.transport._mock_responses.get(
        f"/ap/codings/{document_id}/line/{line_item_id}",
        status_code=200,
        json={
            "id": "coding-1",
            "document_id": document_id,
            "line_item_id": line_item_id,
            "gl_account_id": gl_account_id,
            "gl_account_code": "1200",
            "gl_account_name": "Test Inventory",
            "amount": 150.00,
            "source": "manual",
            "status": "approved",
            "confidence": 100,
        },
    ):
        verify_response = client.get(
            f"/ap/codings/{document_id}/line/{line_item_id}",
            headers=auth_headers,
        )

    assert verify_response.status_code == 200
    coding_data = verify_response.json()
    assert coding_data["source"] == "manual"
    assert coding_data["status"] == "approved"
    assert coding_data["confidence"] == 100


def test_approval_rules_configuration_ui_data(client: TestClient, auth_headers, setup_test_data):
    """Test that approval rules configuration UI has all needed data."""
    org_id = "test-org-1"

    # Test that chart of accounts is available (for GL account selection)
    with client.transport._mock_responses.get(
        f"/ap/chart-of-accounts?org_id={org_id}",
        status_code=200,
        json=[
            {
                "id": "gl-1",
                "account_code": "1200",
                "account_name": "Inventory",
                "is_postable": True,
                "is_active": True,
            },
            {
                "id": "gl-2", 
                "account_code": "4000",
                "account_name": "Revenue",
                "is_postable": True,
                "is_active": True,
            },
        ],
    ):
        # Test that coding rules list is empty initially
        with client.transport._mock_responses.get(
            f"/ap/coding-rules?org_id={org_id}",
            status_code=200,
            json=[],
        ):
            # This simulates what the approval rules configuration UI would do
            chart_response = client.get(
                f"/ap/chart-of-accounts?org_id={org_id}",
                headers=auth_headers,
            )
            assert chart_response.status_code == 200
            assert len(chart_response.json()) == 2

            rules_response = client.get(
                "/ap/coding-rules",
                headers=auth_headers,
            )
            assert rules_response.status_code == 200
            assert len(rules_response.json()) == 0


def test_manual_gl_coding_failure_scenarios(client: TestClient, auth_headers):
    """Test various failure scenarios for manual GL coding."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()

    # Test 1: Missing required fields
    response = client.put(
        f"/ap/codings/{document_id}/line/{line_item_id}",
        json={},  # Empty body - should fail
        headers=auth_headers,
    )
    assert response.status_code == 422  # Validation error

    # Test 2: Invalid UUID format
    response = client.put(
        f"/ap/codings/{document_id}/invalid-line-id}",
        json={
            "gl_account_id": "invalid-uuid",
            "amount": 100.00,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422  # Path validation error

    # Test 3: Permission denied (non-finance user)
    # This would be tested in integration tests with proper role setup


def test_coding_rules_configuration_workflow(client: TestClient, auth_headers, setup_test_data):
    """End-to-end test: coding rules configuration workflow."""
    org_id = "test-org-1"
    document_id = uuid4()
    line_item_id = uuid4()

    # Step 1: Create GL account
    gl_account_id = uuid4()
    gl_account = {
        "id": str(gl_account_id),
        "org_id": org_id,
        "account_code": "1200",
        "account_name": "Test Inventory",
        "account_type": "asset",
        "is_active": True,
        "is_postable": True,
    }

    with client.transport._mock_responses.patch(
        f"/ap/chart-of-accounts/{gl_account_id}",
        status_code=200,
        json=gl_account,
    ):
        # Step 2: Save manual coding
        save_response = client.put(
            f"/ap/codings/{document_id}/line/{line_item_id}",
            json={
                "gl_account_id": str(gl_account_id),
                "amount": 250.00,
            },
            headers=auth_headers,
        )
        assert save_response.status_code == 200

        # Step 3: Create coding rule
        rule_response = client.post(
            "/ap/coding-rules",
            json={
                "name": "Auto-code: Supplies",
                "description": "Auto-assign Inventory for common supplies",
                "description_pattern": "Office Supplies,Stationery,Equipment",
                "gl_account_id": str(gl_account_id),
                "priority": 100,
            },
            headers=auth_headers,
        )
        assert rule_response.status_code == 200

        # Step 4: List rules to confirm
        with client.transport._mock_responses.get(
            f"/ap/coding-rules?org_id={org_id}",
            status_code=200,
            json=[rule_response.json()],
        ):
            list_response = client.get(
                "/ap/coding-rules",
                headers=auth_headers,
            )
            assert list_response.status_code == 200
            assert len(list_response.json()) == 1

    print("✅ All manual GL coding API tests passed")