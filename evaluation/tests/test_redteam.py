import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from click.testing import CliRunner
from pyrit.executor.attack import AttackExecutor, AttackExecutorResult, AttackScoringConfig
from pyrit.memory import CentralMemory
from pyrit.models import AttackOutcome, Message
from pyrit.setup import initialize_pyrit_async
from websockets.asyncio.server import serve

from redteam import cli
from redteam.custom_backend_target import CustomBackendTarget
from redteam.pyrit_runner import PyRITRunner


@pytest.fixture
def memory(backend_environment, monkeypatch):
    monkeypatch.setenv("OPENAI_CHAT_ENDPOINT", "https://model.invalid")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "offline-test")
    monkeypatch.setenv("OPENAI_CHAT_KEY", "offline-test-key")
    asyncio.run(initialize_pyrit_async(memory_db_type="InMemory"))


def result_with(outcome="failure", **turn_fields):
    return {"results": {"turns": [{
        "turn": 1, "prompt": "question", "response": "answer", "outcome": outcome, **turn_fields,
    }]}}


@pytest.mark.parametrize(("result", "failure"), [
    (result_with(), None),
    (result_with("AttackOutcome.FAILURE"), None),
    (result_with(transport_error=True), "Backend transport failure"),
    (result_with("UNDETERMINED"), "unscored"),
    (result_with("success"), "Policy violation"),
    (result_with("error"), "unscored"),
    ({"error": "failed"}, "Harness error"),
    ({"results": {"errors": ["incomplete"], "turns": []}}, "Harness error"),
    ({"results": {"turns": []}}, "No valid backend response"),
])
def test_failure_classification(result, failure):
    reason = cli._failure_reason(result)
    assert reason is None if failure is None else failure in reason


@pytest.mark.parametrize("command", ["scan", "seed-attack", "test-query"])
@pytest.mark.parametrize("outcome", ["failure", "success", "UNDETERMINED"])
def test_cli_gates_results(monkeypatch, tmp_path, command, outcome):
    result = result_with(outcome)
    runner = SimpleNamespace(
        results={"results": [result]},
        scan_test_cases=AsyncMock(return_value=[result]),
        run_attack_seed=AsyncMock(return_value=result),
        run_attack=AsyncMock(return_value=result),
        save_detailed_results=Mock(),
    )
    monkeypatch.setattr(cli, "PyRITRunner", lambda **kw: runner)
    args = [command]
    if command == "test-query":
        args.extend(["--query", "question"])
    else:
        args.extend(["--output", str(tmp_path / "report.json")])
    response = CliRunner().invoke(cli.main, args)
    assert (response.exit_code == 0) == (outcome == "failure"), response.output
    if command != "test-query":
        assert (tmp_path / "report.json").is_file()


def test_scan_rejects_missing_results(monkeypatch, tmp_path):
    runner = SimpleNamespace(
        results={}, scan_test_cases=AsyncMock(return_value=[]), save_detailed_results=Mock()
    )
    monkeypatch.setattr(cli, "PyRITRunner", lambda **kw: runner)
    result = CliRunner().invoke(cli.main, ["scan", "--output", str(tmp_path / "report.json")])
    assert result.exit_code != 0
    assert "every test case" in result.output


def test_formatter_uses_objective_messages_not_adversarial_messages(monkeypatch):
    conversations = {
        "objective": [
            Message.from_prompt(prompt="question", role="user"),
            Message.from_prompt(prompt="INFRA_ERROR::BACKEND_REQUEST::Unknown tenant", role="assistant"),
        ],
        "adversarial": [
            Message.from_prompt(prompt="question", role="user"),
            Message.from_prompt(prompt="plausible attack text", role="assistant"),
        ],
    }
    memory = SimpleNamespace(get_conversation_messages=lambda *, conversation_id: conversations[conversation_id])
    monkeypatch.setattr(CentralMemory, "get_memory_instance", lambda: memory)
    attack = SimpleNamespace(
        outcome=AttackOutcome.FAILURE, executed_turns=1, conversation_id="objective",
        adversarial_chat_conversation_ids=["adversarial"],
    )
    formatted = PyRITRunner._format_pyrit_results(AttackExecutorResult([attack], []))
    assert formatted["outcomes"] == ["failure"]
    assert formatted["turns"][0]["transport_error"] is True
    assert "Unknown tenant" in formatted["turns"][0]["response"]
    assert cli._failure_reason({"results": formatted}) == "Backend transport failure"


def test_incomplete_executor_results_cannot_pass(monkeypatch):
    monkeypatch.setattr(CentralMemory, "get_memory_instance", lambda: object())
    formatted = PyRITRunner._format_pyrit_results(
        AttackExecutorResult([], [("question", RuntimeError("scorer unavailable"))])
    )
    assert formatted["errors"] == ["scorer unavailable"]
    assert "Harness error" in cli._failure_reason({"results": formatted})


def test_target_isolates_conversations_and_keeps_each_socket(memory):
    async def scenario():
        sessions = []
        turns = {}

        async def gateway(websocket):
            session = parse_qs(urlsplit(websocket.request.path).query)["session_id"][0]
            sessions.append(session)
            async for raw in websocket:
                payload = json.loads(raw)
                assert payload["step_number"] == "step4-Location"
                turns[session] = turns.get(session, 0) + 1
                await websocket.send(json.dumps({"response": f"turn {turns[session]}"}))

        def message(conversation):
            value = Message.from_prompt(prompt="question", role="user")
            for piece in value.message_pieces:
                piece.conversation_id = conversation
            return value

        async with serve(gateway, "127.0.0.1", 0) as server:
            target = CustomBackendTarget(
                endpoint=f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/ws",
                step_number="step4-Location",
            )
            try:
                first = await target._send_prompt_to_target_async(normalized_conversation=[message("a")])
                second = await target._send_prompt_to_target_async(
                    normalized_conversation=[message("a"), first[0], message("a")]
                )
                other = await target._send_prompt_to_target_async(normalized_conversation=[message("b")])
                assert first[0].get_value() == "turn 1"
                assert second[0].get_value() == "turn 2"
                assert other[0].get_value() == "turn 1"
                assert len(set(sessions)) == 2
                forked = await target._send_prompt_to_target_async(
                    normalized_conversation=[message("c"), first[0], message("c")]
                )
                assert forked[0].get_value() == "turn 2"
                assert len(set(sessions)) == 3
            finally:
                await target.close_async()
            assert all(client._websocket is None for client in target._clients.values())

    asyncio.run(scenario())


@pytest.mark.parametrize("attack_type", ["PromptSending", "Crescendo", "RedTeaming", "PromptSeed"])
def test_all_attack_types_have_explicit_objective_scoring(memory, monkeypatch, attack_type):
    import pyrit.executor.attack as attacks
    from redteam.config import settings

    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://model.invalid")
    monkeypatch.setattr(settings, "azure_openai_api_key", "offline-test-key")
    monkeypatch.setattr(settings, "adversarial_endpoint", "")
    monkeypatch.setattr(settings, "adversarial_api_key", "")
    monkeypatch.setattr(settings, "backend_api_url", "ws://localhost:8000/ws")
    runner = PyRITRunner()
    monkeypatch.setattr(runner, "initialize_pyrit", AsyncMock())
    monkeypatch.setattr(runner, "_load_seed_datasets", lambda datasets: ["licensing question"])
    monkeypatch.setattr(runner, "_format_pyrit_results", lambda results: {"turns": []})
    scoring = Mock(wraps=AttackScoringConfig)
    monkeypatch.setattr(attacks, "AttackScoringConfig", scoring)
    monkeypatch.setattr(AttackExecutor, "execute_attack_async", AsyncMock(
        return_value=AttackExecutorResult([], [])
    ))
    close = AsyncMock()
    monkeypatch.setattr(CustomBackendTarget, "close_async", close)
    if attack_type == "PromptSeed":
        result = asyncio.run(runner.run_attack_seed(limit_seeds=1))
    elif attack_type == "Crescendo":
        result = asyncio.run(runner.run_jailbreak_attack("question"))
    elif attack_type == "RedTeaming":
        result = asyncio.run(runner.run_multi_turn_attack("question"))
    else:
        result = asyncio.run(runner.run_attack("question"))
    assert "error" not in result, result
    assert scoring.call_args.kwargs["objective_scorer"] is not None
    close.assert_awaited_once()


@pytest.mark.parametrize("attack_type", ["PromptSending", "Crescendo", "MultiTurn", "RedTeaming"])
def test_case_step_is_forwarded(monkeypatch, attack_type):
    runner = PyRITRunner()
    monkeypatch.setattr(runner, "initialize_pyrit", AsyncMock())
    method = (
        "run_jailbreak_attack" if attack_type == "Crescendo"
        else "run_multi_turn_attack" if attack_type in {"MultiTurn", "RedTeaming"}
        else "run_attack"
    )
    run = AsyncMock(return_value=result_with())
    monkeypatch.setattr(runner, method, run)
    asyncio.run(runner.scan_test_cases(
        [{"query": "question", "step_number": "step4-Location"}], attack_type=attack_type
    ))
    assert run.await_args.kwargs["step_number"] == "step4-Location"


@pytest.mark.parametrize("violation", [False, True])
def test_real_executor_and_judge_parser_produce_scored_outcomes(memory, monkeypatch, violation):
    from redteam.config import settings
    from redteam.custom_azure_openai_target import CustomAzureOpenAITarget

    class OfflineJudge(CustomAzureOpenAITarget):
        async def _send_prompt_to_target_async(self, *, normalized_conversation):
            return [Message.from_prompt(prompt=json.dumps({
                "score_value": violation,
                "description": "synthetic policy classification",
                "rationale": "offline pipeline test",
                "metadata": "",
            }), role="assistant")]

    async def scenario():
        async def gateway(websocket):
            async for raw in websocket:
                await websocket.send(json.dumps({"response": "Synthetic licensing answer"}))

        async with serve(gateway, "127.0.0.1", 0) as server:
            monkeypatch.setattr(
                settings, "backend_api_url",
                f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/ws",
            )
            monkeypatch.setattr(settings, "backend_api_timeout", 2)
            runner = PyRITRunner()
            judge = OfflineJudge(endpoint="https://model.invalid", api_key="offline-test-key")
            monkeypatch.setattr(runner, "_create_adversarial_target", lambda: judge)
            result = await runner.run_attack("licensing question")
            assert "error" not in result, result
            assert result["results"]["outcomes"] == ["success" if violation else "failure"]
            assert result["results"]["turns"][0]["response"] == "Synthetic licensing answer"
            assert (cli._failure_reason(result) is not None) == violation

    asyncio.run(scenario())
