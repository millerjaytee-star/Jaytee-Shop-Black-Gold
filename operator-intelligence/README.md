# Stabilis Operator Intelligence(TM)

Verified operating-intelligence and execution system for multi-unit restaurant operators.

Validation states: Synthetic Engine Validation PASSED; Infrastructure/Security Validation PENDING dedicated live Supabase execution; Real-World Engine Calibration PENDING pilots; Customer Value Validation PENDING pilots.

Local quick start: `python scripts/generate_dataset.py`, `python scripts/run_analysis.py`, `python -m src.services.build_gate_c`, `pytest -q`, `uvicorn src.api.app:app --host 127.0.0.1 --port 8000`.

## Integrated Stabilis web + demo application

The reference build combines the public Stabilis brand experience and the Operator Intelligence application in one FastAPI service.

Run locally:

```bash
python -m src.services.build_gate_c
uvicorn src.api.app:app --reload --host 127.0.0.1 --port 8000
```

Key application routes include `/`, `/operator-intelligence`, `/profit-leak-score`, `/demo`, `/demo/locations`, `/demo/opportunities`, `/demo/labor`, `/demo/food-cost`, `/demo/revenue`, `/demo/actions`, `/demo/results`, `/demo/reports`, and `/analyst/demo`.

The Harbor & Hearth demo is fictional test data. The controlled engine reproduces approximately $392,570.56 of modeled recoverable opportunity after deduplication; this is not claimed savings.

## Release gate

Do **not** ingest real restaurant financial data until a dedicated Stabilis Supabase project is provisioned and live RLS/private-storage/cross-tenant security tests pass. Do not reuse Concrete Motivation or unrelated projects.

## Architecture

RAW DATA → VALIDATE → NORMALIZE → CALCULATE → BENCHMARK → DETECT → DIAGNOSE → QUANTIFY → PRIORITIZE → REVIEW → RECOMMEND → ASSIGN → EXECUTE → VERIFY → MEASURE → LEARN.

Financial truth is deterministic and server-controlled. AI is never the calculation layer and cannot self-approve or self-verify customer intelligence.
