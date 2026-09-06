# Stabilis Operator Intelligence(TM)

Verified operating-intelligence and execution system for multi-unit restaurant operators.

Validation states: Synthetic Engine Validation PASSED; Infrastructure/Security Validation PASSED for the dedicated Stabilis environment and controlled-pilot scope documented in [`../docs/security-release-gate.md`](../docs/security-release-gate.md); Real-World Engine Calibration PENDING pilots; Customer Value Validation PENDING pilots.

Local quick start: `python scripts/generate_dataset.py`, `python scripts/run_analysis.py`, `pytest -q`, `uvicorn src.api.app:app --host 127.0.0.1 --port 8000`.

## Integrated Stabilis web + demo application

The reference build combines the public Stabilis brand experience and the Operator Intelligence application in one FastAPI service.

Run locally:

```bash
python scripts/generate_dataset.py
uvicorn src.api.app:app --reload --host 127.0.0.1 --port 8000
```

Key application routes include `/`, `/operator-intelligence`, `/profit-leak-score`, `/demo`, `/demo/locations`, `/demo/opportunities`, `/demo/labor`, `/demo/food-cost`, `/demo/revenue`, `/demo/actions`, `/demo/results`, `/demo/reports`, and `/analyst/demo`.

The Harbor & Hearth demo is fictional test data. The controlled engine reproduces approximately $392,570.56 of modeled recoverable opportunity after deduplication; this is not claimed savings.

## Release gate

The authoritative decision is [`../docs/security-release-gate.md`](../docs/security-release-gate.md). Its current approval is limited to controlled pilots in the dedicated Stabilis environment under the documented tenant, storage, authentication, deterministic-analysis and review controls. Do not reuse Concrete Motivation or unrelated projects, and do not treat this approval as real-world model calibration or customer-value validation.

## Architecture

RAW DATA → VALIDATE → NORMALIZE → CALCULATE → BENCHMARK → DETECT → DIAGNOSE → QUANTIFY → PRIORITIZE → REVIEW → RECOMMEND → ASSIGN → EXECUTE → VERIFY → MEASURE → LEARN.

Financial truth is deterministic and server-controlled. AI is never the calculation layer and cannot self-approve or self-verify customer intelligence.
