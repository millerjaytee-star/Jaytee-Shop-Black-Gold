"""Run the actual labor migration against disposable Postgres and a synthetic auth foundation."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
from uuid import UUID

import pytest

HERE = Path(__file__).resolve().parent
MIGRATION = HERE.parents[1] / "supabase/migrations/20261120220000_weekly_labor_review.sql"
SOURCE_MIGRATION = MIGRATION.with_name("20261120231842_weekly_labor_source_archive.sql")
WEEK = "2025-10-05"
WEEK2 = "2025-10-12"
INPUT = dict(
    forecast_sales=10000,
    actual_sales=9000,
    target_pct=25,
    scheduled_hours=125,
    actual_hours=135,
    scheduled_cost=2500,
    actual_cost=2700,
)
NEXT = dict(INPUT, actual_sales=10000, actual_hours=125, actual_cost=2500)
ACTION_EVIDENCE = {"target_measure": "Paid hours within schedule", "evidence_required": "Daily closing punch totals"}


def uid(number):
    return str(UUID(int=number))


ORG, OTHER_ORG, LOCATION, OTHER_LOCATION, OUTSIDE_LOCATION = map(uid, range(100, 105))
ANALYST, OWNER, GM, SECOND_GM, VIEWER, OUTSIDE, AREA = map(uid, range(1, 8))


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


class Database:
    def __init__(self, bindir, port, password):
        self.psql = str(bindir / "psql")
        self.host = "127.0.0.1"
        self.port = str(port)
        self.env = {**os.environ, "PGPASSWORD": password}

    def run(self, statement, *, actor=None, role="authenticated", error=None):
        if actor or role == "anon":
            principal = f"set request.jwt.claim.sub={literal(actor)};" if actor else ""
            statement = f"set role {role}; set request.storage_operation='storage.object.get_authenticated'; {principal} {statement}"
        result = subprocess.run(
            [
                self.psql,
                "-X",
                "-qAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                self.host,
                "-p",
                self.port,
                "-U",
                "postgres",
                "-d",
                "postgres",
            ],
            env=self.env,
            input=statement,
            text=True,
            capture_output=True,
        )
        if error:
            assert result.returncode, "Unexpected success"
            assert error in result.stderr, result.stderr
            return None
        assert result.returncode == 0, result.stderr
        value = result.stdout.strip()
        return json.loads(value) if value else None

    def save(self, actor, operation, payload, row=None, *, error=None, org=ORG, location=LOCATION):
        review_id = literal(row["id"]) if row else "null"
        version = row["version"] if row else 0
        return self.run(
            f"select public.stabilis_save_labor_review('{org}','{location}',"
            f"{review_id},{version},{literal(operation)},{literal(json.dumps(payload))}::jsonb);",
            actor=actor,
            error=error,
        )

    def read(self, actor, location=LOCATION, org=ORG, **kwargs):
        return self.run(f"select public.stabilis_labor_reviews('{org}','{location}')", actor=actor, **kwargs)


@pytest.fixture(scope="module")
def db():
    initdb = shutil.which("initdb")
    if not initdb and shutil.which("pg_config"):
        candidate = Path(subprocess.check_output(["pg_config", "--bindir"], text=True).strip()) / "initdb"
        if candidate.is_file():
            initdb = str(candidate)
    if not initdb or os.geteuid() == 0:
        pytest.skip("Local PostgreSQL server binaries and an unprivileged account required")
    bindir = Path(initdb).parent
    with tempfile.TemporaryDirectory(prefix="stabilis-labor-") as directory:
        sock = Path(directory)
        data = sock / "db"
        password = secrets.token_urlsafe(32)
        password_file = sock / "password"
        password_file.write_text(password)
        password_file.chmod(0o600)
        with socket.socket() as local:
            local.bind(("127.0.0.1", 0))
            port = local.getsockname()[1]
        subprocess.run(
            [
                initdb,
                "-D",
                str(data),
                "-U",
                "postgres",
                "-A",
                "scram-sha-256",
                "--pwfile",
                str(password_file),
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            capture_output=True,
        )
        control = [str(bindir / "pg_ctl"), "-D", str(data)]
        subprocess.run(
            control
            + [
                "-w",
                "-l",
                str(sock / "postgres.log"),
                "-o",
                f"-h 127.0.0.1 -p {port} -c unix_socket_directories=''",
                "start",
            ],
            check=True,
            capture_output=True,
        )
        try:
            instance = Database(bindir, port, password)
            instance.run((HERE / "foundation.sql").read_text())
            instance.run(MIGRATION.read_text())
            instance.run(SOURCE_MIGRATION.read_text())
            instance.run(
                f"insert into stabilis.organizations values ('{ORG}'),('{OTHER_ORG}');"
                f"insert into stabilis.locations(id,organization_id) values ('{LOCATION}','{ORG}'),('{OTHER_LOCATION}','{ORG}'),"
                f"('{OUTSIDE_LOCATION}','{OTHER_ORG}');"
            )
            for actor, role, org in (
                (ANALYST, "STABILIS_ANALYST", ORG),
                (OWNER, "OWNER_EXECUTIVE", ORG),
                (GM, "GENERAL_MANAGER", ORG),
                (SECOND_GM, "GENERAL_MANAGER", ORG),
                (VIEWER, "READ_ONLY", ORG),
                (OUTSIDE, "OWNER_EXECUTIVE", OTHER_ORG),
                (AREA, "AREA_MANAGER", ORG),
            ):
                instance.run(
                    f"insert into stabilis.profiles values('{actor}');"
                    f"insert into stabilis.memberships(organization_id,profile_id,role,status) values('{org}','{actor}','{role}','ACTIVE');"
                )
            for actor in [GM, SECOND_GM, VIEWER, AREA]:
                instance.run(
                    f"insert into stabilis.membership_locations select id,'{LOCATION}' from stabilis.memberships "
                    f"where profile_id='{actor}';"
                )
            yield instance
        finally:
            subprocess.run(control + ["-m", "immediate", "-w", "stop"], check=True, capture_output=True)


def test_server_math(db):
    def metrics(values):
        return db.run(f"select stabilis.labor_metrics({literal(json.dumps(values))}::jsonb)")

    assert metrics(INPUT) == dict(
        actual_pct=30,
        points_over=5,
        hours_over=10,
        schedule_effect=0,
        sales_effect=250,
        payroll_effect=200,
        total_over=450,
    )
    sales_only = metrics(dict(INPUT, scheduled_cost=2500, actual_cost=2500, actual_hours=125))
    assert [sales_only[k] for k in ("schedule_effect", "sales_effect", "payroll_effect", "total_over")] == [
        0,
        250,
        0,
        250,
    ]
    overbuilt = metrics(dict(NEXT, scheduled_cost=2700, actual_cost=2700))
    assert [overbuilt[k] for k in ("schedule_effect", "sales_effect", "payroll_effect", "total_over")] == [
        200,
        0,
        0,
        200,
    ]
    incomplete = metrics(dict(INPUT, forecast_sales=None, actual_sales=0))
    assert incomplete["actual_pct"] is None and incomplete["hours_over"] == 10
    assert incomplete["sales_effect"] is None and incomplete["schedule_effect"] is None


def create(db, week=WEEK):
    return db.save(ANALYST, "create", {"week_start": week, "inputs": INPUT, "source": "Matched location exports"})


def enroll(db):
    db.run(f"select public.stabilis_enroll_labor_assignee('{ORG}','{LOCATION}','Location GM')", actor=GM)


def assigned(db, week=WEEK):
    enroll(db)
    initial = create(db, week)
    released = db.save(ANALYST, "release", {"note": "Reviewed payroll and forecast"}, initial)
    return db.save(
        OWNER,
        "assign",
        {**ACTION_EVIDENCE, "title": "Review closing hours", "assignee_id": GM, "due_date": "2025-12-10", "next_review": "2025-12-11"},
        released,
    )


def test_permissions_and_draft_revisions(db):
    week = "2025-09-07"
    d = create(db, week)
    assert not any(r["id"] == d["id"] for r in db.read(OWNER))
    assert not any(r["id"] == d["id"] for r in db.read(GM))
    assert create(db, week)["id"] == d["id"]
    db.save(ANALYST, "create", {"week_start": week, "inputs": NEXT, "source": "Corrected"}, error="A review exists")
    revised = db.save(ANALYST, "revise", {"inputs": NEXT, "source": "Corrected paid hours"}, d)
    assert revised["version"] == 2 and revised["metrics"]["total_over"] == 0
    db.save(VIEWER, "release", {"note": "review"}, revised, error="Review unavailable")
    db.read(OUTSIDE, error="Location unavailable")
    db.read(GM, OTHER_LOCATION, error="Location unavailable")
    db.read(OWNER, OUTSIDE_LOCATION, error="Location unavailable")
    db.read(None, role="anon", error="permission denied")
    db.run("select * from stabilis.weekly_labor_reviews", actor=GM, error="permission denied")
    db.run(f"select public.stabilis_labor_assignees('{ORG}','{LOCATION}')", actor=VIEWER, error="Leader access required")


def test_released_correction_requires_review_and_preserves_previous_decision(db):
    initial = assigned(db, "2025-08-03")
    correction = {"inputs": NEXT, "source": "Corrected payroll", "note": "Replace duplicate punch", "week_start": initial["week_start"]}
    db.save(OWNER, "correct", correction, initial, error="Analyst access")
    db.save(ANALYST, "correct", dict(correction, week_start="2025-08-10"), initial, error="original fiscal week")
    revised = db.save(ANALYST, "correct", correction, initial)
    assert revised["id"] == initial["id"] and revised["status"] == "draft"
    assert revised["action"] is None and revised["metrics"]["total_over"] == 0
    assert not any(record["id"] == revised["id"] for record in db.read(OWNER))
    previous = db.run(
        f"select previous_state from stabilis.weekly_labor_audit where review_id='{revised['id']}' and version={revised['version']}"
    )
    assert previous["action"]["assignee_id"] == GM and previous["metrics"]["total_over"] == 450
    released = db.save(ANALYST, "release", {"note": "Corrected payroll checked"}, revised)
    assert any(record["id"] == released["id"] for record in db.read(OWNER))


def test_review_and_retries(db):
    row = assigned(db)
    assert row["status"] == "assigned" and row["verification"] is None
    db.save(SECOND_GM, "accept", {}, row, error="Assigned GM")
    changed = db.save(GM, "request_change", {"note": "Change the due date"}, row)
    row = db.save(
        AREA,
        "assign",
        {**ACTION_EVIDENCE, "title": "Review closing hours", "assignee_id": GM, "due_date": WEEK2, "next_review": WEEK2},
        changed,
    )
    accepted = db.save(GM, "accept", {}, row)
    assert db.save(GM, "accept", {}, row)["version"] == accepted["version"]
    evidence = db.save(GM, "submit_evidence", {"note": "Signed closing schedule in folder A"}, accepted)
    db.save(VIEWER, "clarify", {"note": "Add punches"}, evidence, error="reviewer or leader access required")
    clarified = db.save(OWNER, "clarify", {"note": "Include the paid closing punch totals"}, evidence)
    assert clarified["status"] == "accepted" and clarified["action"].get("evidence") is None
    evidence = db.save(GM, "submit_evidence", {"note": "Closing schedule and punch totals in folder A"}, clarified)
    assert evidence["action"].get("clarification") is None
    compared = db.save(
        ANALYST,
        "compare",
        {
            "week_start": WEEK2,
            "inputs": NEXT,
            "source": "Matched payroll",
            "comparable": True,
            "note": "Same fiscal days and rates",
        },
        evidence,
    )
    assert compared["followup"]["observed_change"] == 450 and compared["verification"] is None
    finance = dict(
        amount=200,
        finance_reference="Client finance approval 87",
        attribution="Signed schedule effect after adjustments",
        overlap_check="Payroll only counted once",
    )
    db.save(ANALYST, "verify", finance, compared, error="Client owner must record")
    db.save(OWNER, "verify", dict(finance, amount=451), compared, error="cannot exceed")
    verified = db.save(OWNER, "verify", finance, compared)
    assert verified["verification"]["amount"] == 200
    reopened = db.save(OWNER, "reopen", {"note": "Recheck opening hours"}, verified)
    assert reopened["status"] == "accepted" and reopened["verification"] is None and reopened["followup"] is None
    assert (
        db.run(
            f"select (previous_state->'verification'->>'amount')::numeric from stabilis.weekly_labor_audit "
            f"where review_id='{verified['id']}' and version={reopened['version']}"
        )
        == 200
    )


def test_incomparable_worse_and_concurrent_updates(db):
    row = assigned(db, "2025-10-19")

    def accept_or_change(op):
        try:
            return db.save(GM, op, {"note": "Manager response"}, row)["status"]
        except AssertionError as exc:
            assert "Refresh before trying again" in str(exc)
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as threads:
        states = list(threads.map(accept_or_change, ["accept", "request_change"]))
    assert states.count("stale") == 1
    row = next(r for r in db.read(GM) if r["id"] == row["id"])
    if row["status"] == "change_requested":
        row = db.save(
            OWNER,
            "assign",
            {**ACTION_EVIDENCE, "title": "Review closing hours", "assignee_id": GM, "due_date": "2025-10-26", "next_review": "2025-10-26"},
            row,
        )
        row = db.save(GM, "accept", {}, row)
    row = db.save(GM, "submit_evidence", {"note": "Revised schedule posted"}, row)
    follow = dict(
        week_start="2025-10-26",
        inputs=dict(INPUT, actual_cost=2800),
        source="Payroll",
        comparable=False,
        note="Different opening hours",
    )
    row = db.save(ANALYST, "compare", follow, row)
    assert row["followup"]["observed_change"] is None
    row = db.save(ANALYST, "compare", dict(follow, comparable=True, note="Matched opening hours after review"), row)
    assert row["followup"]["observed_change"] == -100
    db.save(OWNER, "verify", {"amount": 100}, row, error="positive comparable change")
    assert row["action"]["evidence"] == "Revised schedule posted"
    assert row["followup"]["reviewed_by"] == ANALYST and row["followup"]["reviewed_at"]


def test_revoked_location_grant_removes_roster_and_blocks_actions(db):
    # A manager who once enrolled may no longer work at the pilot site.
    db.run(f"select public.stabilis_enroll_labor_assignee('{ORG}','{LOCATION}','Former GM')", actor=SECOND_GM)
    db.run(
        f"delete from stabilis.membership_locations g using stabilis.memberships m "
        f"where g.membership_id=m.id and m.profile_id='{SECOND_GM}'"
    )
    roster = db.run(f"select public.stabilis_labor_assignees('{ORG}','{LOCATION}')", actor=OWNER)
    assert not any(member["id"] == SECOND_GM for member in roster)
    db.read(SECOND_GM, error="Location unavailable")
    row = create(db, "2025-09-14")
    row = db.save(ANALYST, "release", {"note": "Matched periods checked"}, row)
    db.save(
        OWNER,
        "assign",
        {"title": "Check closes", "assignee_id": SECOND_GM, "due_date": WEEK2, "next_review": WEEK2},
        row,
        error="Choose an enrolled location GM",
    )


def test_no_double_verification_for_same_fiscal_result(db):
    def review(baseline_week):
        row = assigned(db, baseline_week)
        row = db.save(GM, "accept", {}, row)
        row = db.save(GM, "submit_evidence", {"note": "Schedule approved"}, row)
        return db.save(
            ANALYST,
            "compare",
            {
                "week_start": "2025-12-14",
                "inputs": NEXT,
                "source": "Same payroll week",
                "comparable": True,
                "note": "Comparability checked",
            },
            row,
        )

    first = review("2025-11-30")
    second = review("2025-12-07")
    finance = dict(
        amount=100,
        finance_reference="Finance record 123",
        attribution="Schedule correction",
        overlap_check="Payroll index checked",
    )
    db.save(OWNER, "verify", finance, first)
    db.save(OWNER, "verify", finance, second, error="duplicate key")
    unchanged = next(record for record in db.read(OWNER) if record["id"] == second["id"])
    assert unchanged["version"] == second["version"] and unchanged["status"] == "compared"


def test_incomplete_week_and_non_iso_dates(db):
    db.save(
        ANALYST,
        "create",
        {"week_start": "2999-01-01", "inputs": INPUT, "source": "Future"},
        error="Choose a completed fiscal week",
    )
    db.save(ANALYST, "create", {"week_start": "infinity", "inputs": INPUT, "source": "Invalid"}, error="YYYY-MM-DD")


def test_weekly_private_source_storage_and_version_history(db):
    week = "2025-06-01"
    digest = "a" * 64
    retained = "2099-01-01"

    def prepare(actor, location=LOCATION, keep=retained):
        return db.run(
            f"select public.stabilis_prepare_weekly_source('{ORG}','{location}',"
            f"'{week}','payroll.csv','{digest}',10,'{keep}');",
            actor=actor,
        )

    entry = prepare(ANALYST)
    assert not entry["archived"]
    assert prepare(ANALYST) == entry
    with pytest.raises(AssertionError, match="different signed retention"):
        prepare(ANALYST, keep="2099-02-01")
    with pytest.raises(AssertionError, match="Authorized analyst access required"):
        prepare(OWNER)
    path = literal(entry["path"])
    file_id = literal(entry["id"])
    insert = (
        "set request.storage_operation='storage.object.upload';"
        "insert into storage.objects(bucket_id,name,metadata) "
        f"""values ('stabilis-raw',{path},'{{"size":10}}');"""
    )
    complete = f"select public.stabilis_finish_weekly_source('{ORG}','{LOCATION}',{file_id});"
    count = f"select count(*) from storage.objects where name={path};"
    db.run(complete, actor=ANALYST, error="could not be confirmed")
    db.run(insert.replace('storage.object.upload','storage.object.sign_upload_url'), actor=ANALYST, error="row-level security")
    db.run(insert, actor=OWNER, error="row-level security")
    db.run(insert, role="anon", error="row-level security")
    db.run(insert, actor=ANALYST)
    assert db.run(count, actor=ANALYST) == 0
    db.run(complete, actor=ANALYST)
    db.run(complete, actor=ANALYST)
    assert prepare(ANALYST)["archived"]
    assert db.run(count, actor=ANALYST) == 1
    assert db.run("set request.storage_operation='storage.object.sign';"+count, actor=ANALYST) == 0
    assert db.run(count, actor=OWNER) == db.run(count, actor=OUTSIDE) == db.run(count, role="anon") == 0
    db.run(f"delete from storage.objects where name={path};", actor=ANALYST)
    db.run(f"update storage.objects set metadata=null where name={path};", actor=ANALYST)
    assert db.run(count, actor=ANALYST) == 1
    assert db.run(f"select metadata->>'size'::text from storage.objects where name={path};", actor=ANALYST) == 10

    report = {
        "type": "payroll",
        "filename": "payroll.csv",
        "sha256": digest,
        "sheet": "Report",
        "header_row": 1,
        "source_location": "Café",
        "mapping": {"date": "Date", "role": "Job", "daypart": "Service", "actual_hours": "Hours", "actual_cost": "Cost"},
        "totals": {"actual_hours": 135, "actual_cost": 2700},
        "coverage": 7,
        "row_count": 14,
        "groups": [{"role": "Barista", "daypart": "Closing", "actual_hours": 60, "actual_cost": 1200}],
        "gaps": [],
        "archive_id": entry["id"],
    }
    payload = {"week_start": week, "inputs": INPUT, "source": "Mapped review report", "imports": [report]}
    db.save(ANALYST, "create", payload, location=OTHER_LOCATION, error="authorized location and week")
    db.save(ANALYST, "create", dict(payload, inputs=NEXT), error="does not match")
    row = db.save(ANALYST, "create", payload)
    history_query = f"select public.stabilis_weekly_source_history('{ORG}','{LOCATION}','{row['id']}');"
    db.run(history_query, actor=OWNER, error="Source history unavailable")
    db.run(history_query, actor=OUTSIDE, error="Source history unavailable")
    db.run(history_query, role="anon", error="permission denied")
    [initial] = db.run(history_query, actor=ANALYST)
    assert initial["reports"][0]["groups"] == report["groups"]
    assert initial["reports"][0]["archive"]["path"] == entry["path"]

    corrected = db.save(ANALYST, "revise", {"week_start": week, "inputs": NEXT, "source": "Manual corrected report"}, row)
    revisions = db.run(history_query, actor=ANALYST)
    assert [record["version"] for record in revisions] == [2, 1]
    assert revisions[0]["reports"] == [] and revisions[1]["reports"][0]["archive"]["path"] == entry["path"]
    assert corrected["metrics"]["total_over"] == 0
    db.run(f"update stabilis.weekly_labor_source_files set retain_through='2025-06-30' where id={file_id};")
    assert db.run(count, actor=ANALYST) == 0
    assert db.run(history_query, actor=ANALYST)[1]["reports"][0]["archive"]["path"] is None
