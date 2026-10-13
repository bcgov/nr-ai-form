"""Offline regression configuration; no real tenants, datasets, or model credentials."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def backend_environment(monkeypatch):
    monkeypatch.setenv("BACKEND_API_URL", "ws://localhost:8000/ws")
    monkeypatch.setenv("BACKEND_WS_CLIENT_ID", "test-tenant")
    monkeypatch.setenv("BACKEND_WS_ORIGIN", "https://example.invalid")
    monkeypatch.setenv("BACKEND_WS_APPLICATION_ID", "42")
    monkeypatch.setenv("BACKEND_API_TIMEOUT", "1")
    monkeypatch.setenv("BACKEND_WS_STEP", "step2-Eligibility")
