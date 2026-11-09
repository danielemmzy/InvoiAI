import pytest
from pydantic import ValidationError

from app.schemas.workspace import WorkspaceCreate


def test_workspace_currency_defaults_follow_market():
    assert WorkspaceCreate(type="business", country="GB").currency == "GBP"
    assert WorkspaceCreate(type="business", country="US").currency == "USD"
    assert WorkspaceCreate(type="business", country="NG").currency == "NGN"


def test_workspace_currency_can_be_overridden():
    assert WorkspaceCreate(type="business", country="GB", currency="EUR").currency == "EUR"


def test_explicit_empty_currency_is_rejected():
    with pytest.raises(ValidationError):
        WorkspaceCreate(type="business", country="GB", currency="")
