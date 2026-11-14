import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from websockets.asyncio.server import serve

from shared.backend_client import BackendClient, BackendError, extract_text, invoke


@pytest.mark.parametrize("missing", ["client_id", "origin"])
def test_gateway_requires_tenant_configuration(missing):
    with pytest.raises(ValueError, match="configured tenant"):
        BackendClient(**{missing: ""})


@pytest.mark.parametrize("url", ["file:///tmp/test", "localhost:8000", "ws://"])
def test_invalid_backend_url_is_rejected(url):
    with pytest.raises(ValueError, match="BACKEND_API_URL"):
        BackendClient(url)


def test_timeout_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        BackendClient(timeout=0)


def test_persistent_session_and_reconnection():
    async def scenario():
        histories = {}
        connections = []

        async def gateway(websocket):
            params = parse_qs(urlsplit(websocket.request.path).query)
            session_id = params["session_id"][0]
            assert params["channel"] == ["test"]
            assert websocket.request.headers["Origin"] == "https://example.invalid"
            connections.append(session_id)
            history = histories.setdefault(session_id, [])
            await websocket.send(json.dumps({"event": "session_init", "session_id": session_id}))
            async for raw in websocket:
                payload = json.loads(raw)
                assert payload["client_id"] == "test-tenant"
                assert payload["application_id"] == 42
                assert payload["step_number"] == "step4-Location"
                assert payload["session_id"] == session_id
                history.append(payload["query"])
                await websocket.send(json.dumps({
                    "response": [{"response": f"turn {len(history)}"}],
                    "session_id": session_id,
                }))

        async with serve(gateway, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            client = BackendClient(f"ws://127.0.0.1:{port}/ws?channel=test")
            try:
                first = await client.invoke("first", "step4-Location")
                second = await client.invoke("second", "step4-Location")
                assert extract_text(first["response"]) == "turn 1"
                assert extract_text(second["response"]) == "turn 2"
                assert len(connections) == 1
                await client.close()
                third = await client.invoke("third", "step4-Location")
                assert extract_text(third["response"]) == "turn 3"
                assert connections == [client.session_id, client.session_id]
            finally:
                await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("reason", ["Unknown tenant", "Origin not allowed"])
def test_policy_close_is_an_explicit_error(reason):
    async def scenario():
        async def gateway(websocket):
            await websocket.recv()
            await websocket.close(code=1008, reason=reason)

        async with serve(gateway, "127.0.0.1", 0) as server:
            client = BackendClient(f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/ws")
            with pytest.raises(BackendError, match=f"code=1008 reason={reason}"):
                await client.invoke("hello")
            assert client._websocket is None

    asyncio.run(scenario())


@pytest.mark.parametrize("frame", [
    "not json", "[]", "{}", '{"response": ""}', '{"error": "Agent server error"}',
    '{"event": "session_init"}',
])
def test_non_answers_are_not_successful_responses(frame):
    async def scenario():
        async def gateway(websocket):
            await websocket.recv()
            await websocket.send(frame)
            await websocket.wait_closed()

        async with serve(gateway, "127.0.0.1", 0) as server:
            client = BackendClient(f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/ws")
            with pytest.raises(BackendError):
                await client.invoke("hello")
            assert client._websocket is None

    asyncio.run(scenario())


def test_timeout_closes_connection():
    async def scenario():
        async def gateway(websocket):
            await websocket.recv()
            await websocket.wait_closed()

        async with serve(gateway, "127.0.0.1", 0) as server:
            client = BackendClient(
                f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/ws", timeout=0.05
            )
            with pytest.raises(BackendError, match="timed out"):
                await client.invoke("hello")
            assert client._websocket is None

    asyncio.run(scenario())


def test_explicit_http_stand_in_preserves_contract(monkeypatch):
    requests = []

    def handler(request):
        assert str(request.url) == "http://stand-in.invalid/invoke"
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"response": "answer", "session_id": "http-session"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw
    ))
    body = invoke("question", "step4-Location", "http-session", "http://stand-in.invalid/invoke")
    assert body["response"] == "answer"
    assert requests == [{
        "query": "question", "step_number": "step4-Location", "session_id": "http-session",
    }]


def test_promptfoo_surfaces_transport_errors(monkeypatch):
    from promptfoo.providers import backend_provider

    def failed_invoke(**kwargs):
        raise BackendError("Unknown tenant")

    monkeypatch.setattr(backend_provider, "invoke", failed_invoke)
    result = backend_provider.call_api("question", {}, {})
    assert result == {"error": "backend invoke failed: Unknown tenant"}


def test_async_redteam_adapter_uses_shared_transport(monkeypatch):
    from redteam import backend_client

    async def shared_invoke(*args):
        assert args == ("question", "step4-Location", "session", "ws://example.invalid/ws")
        return {"response": "answer"}

    monkeypatch.setattr(backend_client, "invoke_async", shared_invoke)
    result = asyncio.run(backend_client.BackendClient("ws://example.invalid/ws").invoke(
        query="question", step_number="step4-Location", session_id="session"
    ))
    assert result == {"response": "answer"}
