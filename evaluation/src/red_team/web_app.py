from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import settings
from src.red_team.orchestrator import RedTeamOrchestrator
from src.red_team.pyrit_runner import PyRITRunner

BASE_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True, parents=True)
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

AttackType = Literal["PromptSending", "Crescendo", "MultiTurn", "RedTeaming", "PromptSeed"]


class RunScanRequest(BaseModel):
    attack_type: AttackType = "PromptSending"
    use_file: bool = True
    cases: str | None = None
    threat_models: str | None = None
    max_iterations: int = Field(default_factory=lambda: settings.red_team_max_iterations)


class RunSeedAttackRequest(BaseModel):
    datasets: str | None = None
    limit_seeds: int | None = None
    verbose: bool = False


def _save_report(report: dict[str, Any], filename: str | None = None) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if filename is None:
        filename = f"report_{timestamp}.json"
    path = RESULTS_DIR / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def _load_cases(case_names: str | None = None) -> list[dict[str, Any]]:
    all_cases = RedTeamOrchestrator.load_test_cases()
    if not all_cases:
        return [{"query": "What is the application fee for a water licence?"}]

    if case_names:
        allowed = {name.strip() for name in case_names.split(",") if name.strip()}
        selected = [case for case in all_cases if case.get("name") in allowed]
        return selected or all_cases

    return all_cases


def _normalized_turns(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        turns = value.get("turns", [])
        if isinstance(turns, list):
            return [entry for entry in turns if isinstance(entry, dict)]
        return []
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    return []


def _summarize_report(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {"attack_type": None, "seed_datasets": [], "total_turns": 0, "turn_count": 0, "status": "error"}

    results = report.get("results", {})
    if isinstance(results, dict):
        turns = _normalized_turns(results)
        total_turns = results.get("total_turns", len(turns))
        case_count = 1 if turns or results else 0
    elif isinstance(results, list):
        turns = []
        for item in results:
            if isinstance(item, dict):
                turns.extend(_normalized_turns(item.get("results", {})))
        total_turns = len(turns)
        case_count = len([item for item in results if isinstance(item, dict)])
    else:
        turns = []
        total_turns = 0
        case_count = 0

    error_count = 0
    successful_turns = 0
    outcome_counts: dict[str, int] = {}
    for item in turns:
        outcome = str(item.get("outcome") or item.get("status") or "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        if "error" in outcome.lower() or item.get("transport_error") or item.get("error"):
            error_count += 1
        elif outcome and "unknown" not in outcome.lower():
            successful_turns += 1

    return {
        "attack_type": report.get("attack_type"),
        "seed_datasets": report.get("seed_datasets", []),
        "total_turns": total_turns,
        "turn_count": len(turns),
        "successful_turns": successful_turns,
        "error_count": error_count,
        "total_cases": case_count,
        "outcome_counts": outcome_counts,
        "status": "ok" if "error" not in report else "error",
    }


def _report_insights(report: dict[str, Any]) -> dict[str, Any]:
    summary = _summarize_report(report)
    raw_results = report.get("results", [])
    if isinstance(raw_results, dict):
        case_entries = [raw_results]
    elif isinstance(raw_results, list):
        case_entries = [entry for entry in raw_results if isinstance(entry, dict)]
    else:
        case_entries = []

    attack_breakdown: dict[str, dict[str, Any]] = {}
    outcome_distribution: dict[str, dict[str, Any]] = {}
    execution_timeline: list[dict[str, Any]] = []
    case_drilldown: list[dict[str, Any]] = []

    for idx, item in enumerate(case_entries, start=1):
        attack_name = str(item.get("attack_type") or report.get("attack_type") or "unknown")
        attack_entry = attack_breakdown.setdefault(attack_name, {"name": attack_name, "count": 0, "queries": []})
        attack_entry["count"] += 1
        query = str(item.get("query") or item.get("prompt") or "").strip()
        if query:
            attack_entry["queries"].append(query)

        case_turns = _normalized_turns(item.get("results", {}))
        if case_turns:
            for turn in case_turns[:3]:
                outcome_name = str(turn.get("outcome") or turn.get("status") or "unknown")
                entry = outcome_distribution.setdefault(outcome_name, {"name": outcome_name, "count": 0})
                entry["count"] = entry.get("count", 0) + 1

            latest_turn = case_turns[0]
            response_preview = str(latest_turn.get("response") or "").strip()
            prompt_preview = str(latest_turn.get("prompt") or query or "").strip()
        else:
            response_preview = ""
            prompt_preview = query

        execution_timeline.append({
            "step": idx,
            "query": query,
            "attack_type": attack_name,
            "turn_count": len(case_turns),
            "outcome": str(case_turns[0].get("outcome") if case_turns else "unknown").upper(),
            "prompt": prompt_preview[:180],
            "response": response_preview[:220],
        })

        case_drilldown.append({
            "attack_type": attack_name,
            "query": query,
            "turn_count": len(case_turns),
            "response_preview": response_preview[:220],
        })

    timeline = execution_timeline[:12]
    return {
        "summary": {
            **summary,
            "total_cases": len(case_entries) or summary.get("total_cases", 0),
        },
        "timeline": timeline,
        "execution_timeline": timeline,
        "attack_breakdown": sorted(attack_breakdown.values(), key=lambda item: item["count"], reverse=True),
        "outcome_distribution": sorted(outcome_distribution.values(), key=lambda item: item["count"], reverse=True),
        "case_drilldown": case_drilldown,
        "report_metadata": {
            "attack_type": report.get("attack_type"),
            "timestamp": report.get("timestamp"),
            "threat_models": report.get("threat_models", []),
            "seed_datasets": report.get("seed_datasets", []),
        },
    }


app = FastAPI(
    title="NR AI Red Team Browser",
    description="Browser-based runner for PyRIT red-team evaluations and JSON report viewing.",
    version="0.1.0",
)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "results_dir": str(RESULTS_DIR),
        "reports": [p.name for p in sorted(RESULTS_DIR.glob("*.json"))],
    }


@app.get("/api/reports")
async def list_reports() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(RESULTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "name": path.name,
                    "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
                    "summary": _summarize_report(data),
                    "size": path.stat().st_size,
                }
            )
        except Exception:
            items.append({
                "name": path.name,
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
                "summary": {"status": "unreadable"},
                "size": path.stat().st_size,
            })
    return items


@app.get("/api/reports/summary")
async def report_summary() -> dict[str, Any]:
    reports = await list_reports()
    total = len(reports)
    success = sum(1 for item in reports if str(item.get("summary", {}).get("status", "")).lower() == "ok")
    unreadable = sum(1 for item in reports if str(item.get("summary", {}).get("status", "")).lower() == "unreadable")
    error = sum(1 for item in reports if str(item.get("summary", {}).get("status", "")).lower() not in {"ok", "unreadable"})
    last_updated = max((item.get("updated_at") for item in reports), default=None)

    return {
        "total_reports": total,
        "successful_reports": success,
        "error_reports": error,
        "unreadable_reports": unreadable,
        "last_updated": last_updated,
    }


@app.get("/api/reports/{report_name}")
async def get_report(report_name: str) -> dict[str, Any]:
    path = RESULTS_DIR / report_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON report: {exc}") from exc


@app.get("/api/reports/{report_name}/insights")
async def get_report_insights(report_name: str) -> dict[str, Any]:
    path = RESULTS_DIR / report_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON report: {exc}") from exc
    return _report_insights(data)


@app.post("/api/run-scan")
async def run_scan(request: RunScanRequest) -> dict[str, Any]:
    models = [m.strip() for m in (request.threat_models or settings.red_team_threat_models).split(",") if m.strip()]
    runner = PyRITRunner(threat_models=models, max_iterations=request.max_iterations, verbose=True)

    if request.use_file:
        test_cases = _load_cases(request.cases)
    else:
        test_cases = [{"query": "What is the application fee for a water licence?"}]

    if not test_cases:
        raise HTTPException(status_code=400, detail="No test cases available to run.")

    results = await asyncio.to_thread(
        lambda: asyncio.run(runner.scan_test_cases(test_cases, attack_type=request.attack_type))
    )

    if results and any("error" in result for result in results):
        status_code = 400
    else:
        status_code = 200

    report = {
        "report_type": "PyRIT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attack_type": request.attack_type,
        "threat_models": models,
        **runner.results,
    }
    report_path = _save_report(report, filename=f"scan_{request.attack_type.lower()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")

    return {
        "status": "success" if status_code == 200 else "error",
        "report_name": report_path.name,
        "report_path": str(report_path),
        "summary": _summarize_report(report),
        "results": results,
    }


@app.post("/api/run-seed-attack")
async def run_seed_attack(request: RunSeedAttackRequest) -> dict[str, Any]:
    runner = PyRITRunner(verbose=request.verbose)
    selected = None
    if request.datasets:
        if request.datasets.lower() == "all":
            selected = list(runner.available_seed_datasets.keys())
        else:
            selected = [d.strip() for d in request.datasets.split(",") if d.strip()]

    result = await asyncio.to_thread(
        lambda: asyncio.run(
            runner.run_attack_seed(seed_datasets=selected, limit_seeds=request.limit_seeds)
        )
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    report_path = _save_report(result, filename=f"seed_attack_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
    return {
        "status": "success",
        "report_name": report_path.name,
        "report_path": str(report_path),
        "summary": _summarize_report(result),
        "result": result,
    }


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def main() -> None:
    import uvicorn

    uvicorn.run("src.red_team.web_app:app", host="0.0.0.0", port=8011, reload=True)


if __name__ == "__main__":
    main()
