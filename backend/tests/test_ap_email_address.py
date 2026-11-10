from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.ap.email_address_service import manage_email_address


def test_rotation_migration_bootstraps_address_table_for_fresh_database():
    from pathlib import Path

    migration = Path(__file__).parents[1] / "migrations" / "20261109_ap_email_address_rotation.sql"
    sql = migration.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.ap_email_intake_addresses" in sql
    assert "org_id uuid not null references public.organizations(id)" in sql
    assert "email_address text not null" in sql
    assert "is_active boolean not null" in sql
    assert "created_by uuid" in sql


class RPCDatabase:
    def __init__(self):
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=[{
            "org_id": params["p_org_id"],
            "email_address": params["p_email_address"],
            "is_active": True,
            "created_by": params["p_created_by"],
        }]))


def setup_rpc(db):
    calls = []

    def rpc(name, params):
        calls.append((name, params))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=[{
            "org_id": params["p_org_id"],
            "email_address": params["p_email_address"],
            "is_active": True,
            "created_by": params["p_created_by"],
        }]))

    db.rpc = rpc
    return calls


@pytest.mark.parametrize("rotate", [False, True])
def test_address_management_uses_secure_transaction_rpc(rotate):
    db = RPCDatabase()
    org_id, user_id = uuid4(), uuid4()

    result = manage_email_address(db, org_id=org_id, user_id=user_id, domain="inbound.example.com", rotate=rotate)

    assert db.calls[0][0] == "manage_ap_email_intake_address"
    params = db.calls[0][1]
    assert params["p_org_id"] == str(org_id)
    assert params["p_created_by"] == str(user_id)
    assert params["p_rotate"] is rotate
    local = result["email_address"].split("@", 1)[0]
    assert local.startswith("invoices+")
    assert len(local.removeprefix("invoices+")) == 48
    assert result["is_active"] is True


def test_create_address_endpoint_uses_create_or_get_rpc(ap_api, monkeypatch):
    import app.routers.ap as ap_router

    monkeypatch.setattr(ap_router.settings, "ap_email_inbound_domain", "inbound.example.com")
    calls = setup_rpc(ap_api.db)
    response = ap_api.client.post("/api/v2/ap/email-address")

    assert response.status_code == 200
    assert calls[0][0] == "manage_ap_email_intake_address"
    assert calls[0][1]["p_rotate"] is False
    assert response.json()["email_address"].endswith("@inbound.example.com")


def test_admin_rotation_endpoint_replaces_address_atomically(ap_api, monkeypatch):
    import app.routers.ap as ap_router

    monkeypatch.setattr(ap_router.settings, "ap_email_inbound_domain", "inbound.example.com")
    calls = setup_rpc(ap_api.db)
    response = ap_api.client.post("/api/v2/ap/email-address/rotate")

    assert response.status_code == 200
    assert calls[0][0] == "manage_ap_email_intake_address"
    assert calls[0][1]["p_rotate"] is True
    assert calls[0][1]["p_org_id"] == str(ap_api.org_id)
    assert calls[0][1]["p_created_by"] == str(ap_api.user_id)


def test_non_admin_cannot_rotate_address(ap_api):
    from app.core.permissions import MANAGE_FINANCE

    ap_api.context.permissions = ap_api.context.permissions - {MANAGE_FINANCE}
    calls = setup_rpc(ap_api.db)
    response = ap_api.client.post("/api/v2/ap/email-address/rotate")

    assert response.status_code == 403
    assert calls == []


def test_finance_manager_cannot_create_forwarding_address(ap_api):
    from app.core.enum.database import OrgRole

    ap_api.context.role = OrgRole.FINANCE_MANAGER
    calls = setup_rpc(ap_api.db)
    response = ap_api.client.post("/api/v2/ap/email-address")

    assert response.status_code == 403
    assert calls == []


def test_finance_manager_cannot_rotate_address(ap_api):
    from app.core.enum.database import OrgRole

    ap_api.context.role = OrgRole.FINANCE_MANAGER
    calls = setup_rpc(ap_api.db)
    response = ap_api.client.post("/api/v2/ap/email-address/rotate")

    assert response.status_code == 403
    assert calls == []
