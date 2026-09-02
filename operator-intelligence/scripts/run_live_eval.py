"""Run the release live-model golden suite as short OIDC-authenticated requests.

The Netlify function executes one model case at a time. This runner owns concurrency,
aggregation, retries for transient HTTP failures, and the persisted release artifact.
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
TOKEN = os.environ["STABILIS_GOLDEN_OIDC_TOKEN"]
OUT = Path(os.environ.get("STABILIS_GOLDEN_OUTPUT", "outputs/ask-stabilis-live-eval.json"))
TRANSIENT = {429, 502, 503, 504}
MAX_WORKERS = 4


def request_case(case: dict, run: int) -> dict:
    payload = {"case_id": case["id"], "run": run}
    last_error = ""
    for attempt in range(3):
        try:
            with httpx.Client(timeout=40.0) as client:
                response = client.post(
                    f"{BASE}/api/stabilis-golden-eval",
                    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
                    json=payload,
                )
            if response.status_code == 200:
                return response.json()
            last_error = f"HTTP {response.status_code}: {response.text[:800]}"
            if response.status_code not in TRANSIENT:
                break
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < 2:
            time.sleep(2**attempt)
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
        failed = [
            name
            for name, score in result["evaluation"]["scores"].items()
            if score.get("applicable") and int(score.get("score", 0)) < 2
        ]
        if failed:
            critical_failures.append({"case_id": result["case_id"], "run": result["run"], "dimensions": failed})

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

    results.sort(key=lambda row: (next(i for i, c in enumerate(SPEC["cases"]) if c["id"] == row["case_id"]), row["run"]))
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
