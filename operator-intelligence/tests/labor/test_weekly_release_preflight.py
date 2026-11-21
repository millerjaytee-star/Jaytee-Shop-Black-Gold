from pathlib import Path

from test_postgres_labor_review import db as db  # Imported pytest fixture.


PREFLIGHT = Path(__file__).resolve().parents[2] / "scripts" / "weekly_release_preflight.sql"


def test_preflight_detects_a_public_raw_bucket(db):
    sql = PREFLIGHT.read_text()
    state = db.run(sql)
    assert state["foundation"] == "structural checks passed"
    assert state["weekly_reviews"] and state["weekly_source_history"]

    db.run("update storage.buckets set public=true where id='stabilis-raw';")
    try:
        db.run(sql, error="The raw bucket must be private")
    finally:
        db.run("update storage.buckets set public=false where id='stabilis-raw';")

    assert db.run(sql) == state
