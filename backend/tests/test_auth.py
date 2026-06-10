"""
Tests for login error discrimination.

A user who registered but hasn't confirmed their email must get a clear,
actionable message — not "Invalid email or password", which sends them down a
password-reset rabbit hole. Supabase raises AuthApiError(code="email_not_confirmed")
for that case; genuine bad credentials raise code="invalid_credentials".
"""

import asyncio

import pytest
from fastapi import HTTPException

from api.v1 import auth as auth_module
from api.v1.auth import AuthRequest


class _FakeAuthError(Exception):
    """Mimics supabase_auth.AuthApiError (has a .code attribute)."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def _fake_supabase(raise_code):
    class FakeAuth:
        def sign_in_with_password(self, _creds):
            raise _FakeAuthError("boom", raise_code)

    class FakeSB:
        auth = FakeAuth()

    return lambda: FakeSB()


def _login(monkeypatch, code):
    monkeypatch.setattr(auth_module, "get_supabase", _fake_supabase(code))
    return asyncio.run(auth_module.login(AuthRequest(email="user@example.com", password="pw123456")))


def test_unconfirmed_email_gives_clear_message(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _login(monkeypatch, "email_not_confirmed")
    assert ei.value.status_code == 403
    assert "confirm" in ei.value.detail.lower()


def test_bad_credentials_still_generic_401(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _login(monkeypatch, "invalid_credentials")
    assert ei.value.status_code == 401
    assert ei.value.detail == "Invalid email or password"
