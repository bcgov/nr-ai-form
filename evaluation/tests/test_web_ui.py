import os

from fastapi.testclient import TestClient

from src.red_team.custom_backend_target import CustomBackendTarget
from src.red_team.web_app import _report_insights, _summarize_report, app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_reports_endpoint_returns_list():
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_local_backend_disables_proxy_env(monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "socks5h://localhost:57759")
    monkeypatch.setenv("HTTP_PROXY", "http://localhost:57758")
    monkeypatch.setenv("HTTPS_PROXY", "http://localhost:57758")

    captured = {}

    class FakeSocket:
        async def send(self, *args, **kwargs):
            return None

        async def recv(self):
            raise AssertionError("socket should not be used during this unit test")

    async def fake_connect(uri, **kwargs):
        captured["uri"] = uri
        captured["kwargs"] = kwargs
        return FakeSocket()

    import websockets

    monkeypatch.setattr(websockets, "connect", fake_connect)

    target = CustomBackendTarget(endpoint="http://localhost:8000")
    import asyncio
    asyncio.run(target._ensure_websocket_connected())

    assert captured["kwargs"].get("proxy") is None
    assert os.environ.get("ALL_PROXY") is None
    assert os.environ.get("HTTP_PROXY") is None
    assert os.environ.get("HTTPS_PROXY") is None


def test_summarize_report_handles_list_results():
    report = {
        "attack_type": "PromptSending",
        "results": [
            {"prompt": "hello", "response": "world", "outcome": "ok"},
            {"prompt": "next", "response": "done", "outcome": "ok"},
        ],
    }

    summary = _summarize_report(report)

    assert summary["attack_type"] == "PromptSending"
    assert summary["turn_count"] == 2
    assert summary["total_turns"] == 2
    assert summary["status"] == "ok"


def test_report_insights_include_attack_breakdown_and_timeline():
    report = {
        "attack_type": "PromptSending",
        "results": [
            {
                "attack_type": "PromptSendingAttack",
                "results": {
                    "total_turns": 1,
                    "turns": [
                        {"prompt": "Prompt 1", "response": "Response 1", "outcome": "AttackOutcome.UNDETERMINED"}
                    ],
                },
                "query": "Question 1",
            },
            {
                "attack_type": "PromptSendingAttack",
                "results": {
                    "total_turns": 2,
                    "turns": [
                        {"prompt": "Prompt 2a", "response": "Response 2a", "outcome": "AttackOutcome.SUCCESS"},
                        {"prompt": "Prompt 2b", "response": "Response 2b", "outcome": "AttackOutcome.SUCCESS"},
                    ],
                },
                "query": "Question 2",
            },
        ],
    }

    insights = _report_insights(report)

    assert insights["summary"]["total_cases"] == 2
    assert insights["attack_breakdown"][0]["name"] == "PromptSendingAttack"
    assert insights["execution_timeline"][0]["query"] == "Question 1"
    assert insights["outcome_distribution"][0]["name"] == "AttackOutcome.UNDETERMINED"
