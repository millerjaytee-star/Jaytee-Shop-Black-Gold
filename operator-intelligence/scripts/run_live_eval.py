"""Run the release live-model golden suite as short OIDC-authenticated requests.

Each request mints a fresh GitHub OIDC token. Critical financial/security dimensions
must pass every run; noncritical quality dimensions use their explicit thresholds.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "evals/ask_stabilis_golden_v1.json").read_text(encoding="utf-8"))
BASE = os.environ["STABILIS_RELEASE_BASE_URL"].rstrip("/")
OIDC_URL = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
OIDC_REQUEST_TOKEN = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
OUT = Path(os.environ.get("STABILIS_GOLDEN_OUTPUT", "outputs/ask-stabilis-live-eval.json"))
TRANSIENT = {429, 502, 503, 504}
MAX_WORKERS = 6


def fresh_oidc_token() -> str:
    separator = "&" if "?" in OIDC_URL else "?"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            f"{OIDC_URL}{separator}audience=stabilis-golden-eval",
            headers={"Authorization": f"bearer {OIDC_REQUEST_TOKEN}"},
        )
    response.raise_for_status()
    token = str(response.json().get("value") or "")
    if not token:
        raise RuntimeError("GitHub OIDC token response did not contain a value")
    return token


def request_case(case: dict, run: int) -> dict:
    payload = {"case_id": case["id"], "run": run}
    last_error = ""
    for attempt in range(2):
        try:
            oidc_token = fresh_oidc_token()
            with httpx.Client(timeout=45.0) as client:
                response = client.post(
                    f"{BASE}/api/stabilis-golden-eval",
                    headers={"Authorization": f"Bearer {oidc_token}", "Content-Type": "application/json"},
                    json=payload,
                )
            if response.status_code == 200:
                return response.json()
            last_error = f"HTTP {response.status_code}: {response.text[:800]}"
            if response.status_code not in TRANSIENT:
                break
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < 1:
            time.sleep(2)
    raise RuntimeError(f"{case['id']} run {run} failed after retries: {last_error}")


def summarize(results: list[dict]) -> dict:
    dimensions = [
        "factual_grounding",
        "financial_correctness",
        "evidence_quality",
        "authorization",
        "data_gap_behavior",
        "confidence_calibration",
        "refusal_correctness",
        "recommendation_quality",
        "concision",
        "brand_tone",
    ]
    dimension_scores: dict[str, float | None] = {}
    for dimension in dimensions:
        values = []
        for result in results:
            score = result["evaluation"]["scores"].get(dimension, {})
            if score.get("applicable"):
                values.append(float(score["score"]) / 2.0)
        dimension_scores[dimension] = round(sum(values) / len(values), 4) if values else None

    critical_failures = []
    for result in results:
        if not result.get("critical"):
            continue
        required = set(result.get("critical_dimensions") or [])
        failed = [
            name
            for name in required
            if int(result["evaluation"]["scores"].get(name, {}).get("score", 0)) < 2
        ]
        if failed:
            critical_failures.append({"case_id": result["case_id"], "run": result["run"], "dimensions": sorted(failed)})

    thresholds = SPEC["scoring"]
    gates = {
        "financial_correctness": dimension_scores["financial_correctness"] == 1.0,
        "authorization_refusal": dimension_scores["authorization"] == 1.0 and dimension_scores["refusal_correctness"] == 1.0,
        "evidence_grounding": (dimension_scores["evidence_quality"] or 0.0) >= thresholds["evidence_grounding_min"],
        "data_gap_correctness": (dimension_scores["data_gap_behavior"] or 0.0) >= thresholds["data_gap_min"],
        "recommendation_quality": (dimension_scores["recommendation_quality"] or 0.0) >= thresholds["recommendation_quality_min"],
        "brand_tone": (dimension_scores["brand_tone"] or 0.0) >= thresholds["brand_tone_min"],
        "critical_cases": not critical_failures,
    }
    return {"dimension_scores": dimension_scores, "gates": gates, "critical_failures": critical_failures}


def main() -> None:
    tasks: list[tuple[dict, int]] = []
    for case in SPEC["cases"]:
        for run in range(1, int(case.get("repeats", 1)) + 1):
            tasks.append((case, run))

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {pool.submit(request_case, case, run): (case["id"], run) for case, run in tasks}
        for future in as_completed(future_map):
            results.append(future.result())

    case_order = {case["id"]: i for i, case in enumerate(SPEC["cases"])}
    results.sort(key=lambda row: (case_order[row["case_id"]], row["run"]))
    summary = summarize(results)
    status = "PASS" if all(summary["gates"].values()) else "FAIL"
    total_tokens = sum(int(row.get("usage", {}).get("totalTokens") or 0) for row in results)
    total_cost = sum(float(row.get("approximate_cost", {}).get("usd") or 0) for row in results)
    artifact = {
        "evaluation_version": SPEC["evaluation_version"],
        "fixture": "Harbor & Hearth Restaurant Group",
        "fixture_version": SPEC["context_builder_version"],
        "fictional_fixture": True,
        "timestamp": max(row["timestamp"] for row in results),
        "provider": results[0]["provider"] if results else None,
        "requested_model": "gpt-5",
        "prompt_version": SPEC["prompt_version"],
        "context_builder_version": SPEC["context_builder_version"],
        "question_count": len(SPEC["cases"]),
        "model_call_count": len(results),
        "total_provider_tokens": total_tokens,
        "approximate_total_cost_usd": round(total_cost, 8),
        **summary,
        "results": results,
        "status": status,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(
        f"ASK STABILIS LIVE GOLDEN ORCHESTRATOR = {status} | "
        f"questions={artifact['question_count']} calls={artifact['model_call_count']} "
        f"tokens={total_tokens} approximate_cost_usd={artifact['approximate_total_cost_usd']}"
    )


if __name__ == "__main__":
    main()
