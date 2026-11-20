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
WEEK = "2026-10-05"
WEEK2 = "2026-10-12"
INPUT = dict(forecast_sales=10000, actual_sales=9000, target_pct=25, scheduled_hours=125,
             actual_hours=135, scheduled_cost=2500, actual_cost=2700)
NEXT = dict(INPUT, actual_sales=10000, actual_hours=125, actual_cost=2500)


def uid(number):
    return str(UUID(int=number))


ORG, OTHER_ORG, LOCATION, OTHER_LOCATION, OUTSIDE_LOCATION = map(uid, range(100, 105))
ANALYST, OWNER, GM, SECOND_GM, VIEWER, OUTSIDE, AREA = map(uid, range(1, 8))


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


class Database:
    def __init__(self, bindir, port, password):
        self.psql = str(bindir / "psql")
        self.host = '127.0.0.1'
        self.port = str(port)
        self.env = {**os.environ, 'PGPASSWORD': password}

    def run(self, statement, *, actor=None, role="authenticated", error=None):
        if actor or role == "anon":
            principal = f"set request.jwt.claim.sub={literal(actor)};" if actor else ""
            statement = f"set role {role}; {principal} {statement}"
        result = subprocess.run([self.psql, "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
                                 "-h", self.host, "-p", self.port, "-U", "postgres", "-d", "postgres"],
                                env=self.env,
                                input=statement, text=True, capture_output=True)
        if error:
            assert result.returncode, "Unexpected success"
            assert error in result.stderr, result.stderr
            return None
        assert result.returncode == 0, result.stderr
        value = result.stdout.strip()
        return json.loads(value) if value else None

    def save(self, actor, operation, payload, row=None, *, error=None, org=ORG, location=LOCATION):
        review_id = literal(row['id']) if row else "null"
        version = row['version'] if row else 0
        return self.run(f"select public.stabilis_save_labor_review('{org}','{location}',"
                        f"{review_id},{version},{literal(operation)},{literal(json.dumps(payload))}::jsonb);",
                        actor=actor, error=error)

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
            local.bind(("127.0.0.1",0))
            port = local.getsockname()[1]
        subprocess.run([initdb, "-D", str(data), "-U", "postgres", "-A", "scram-sha-256",
                        "--pwfile", str(password_file), "--no-locale", "--encoding=UTF8"],
                       check=True, capture_output=True)
        control = [str(bindir / "pg_ctl"), "-D", str(data)]
        subprocess.run(control + ["-w", "-l", str(sock / "postgres.log"), "-o",
                                  f"-h 127.0.0.1 -p {port} -c unix_socket_directories=''", "start"], check=True, capture_output=True)
        try:
            instance = Database(bindir, port, password)
            instance.run((HERE / "foundation.sql").read_text())
            instance.run(MIGRATION.read_text())
            instance.run(f"insert into stabilis.organizations values ('{ORG}'),('{OTHER_ORG}');"
                         f"insert into stabilis.locations values ('{LOCATION}','{ORG}'),('{OTHER_LOCATION}','{ORG}'),"
                         f"('{OUTSIDE_LOCATION}','{OTHER_ORG}');")
            for actor, role, org in ((ANALYST, "STABILIS_ANALYST", ORG), (OWNER, "OWNER_EXECUTIVE", ORG),
                                     (GM, "GENERAL_MANAGER", ORG), (SECOND_GM, "GENERAL_MANAGER", ORG),
                                     (VIEWER, "READ_ONLY", ORG), (OUTSIDE, "OWNER_EXECUTIVE", OTHER_ORG),
                                     (AREA, "AREA_MANAGER", ORG)):
                instance.run(f"insert into stabilis.profiles values('{actor}');"
                             f"insert into stabilis.memberships values('{org}','{actor}','{role}','ACTIVE');")
            for actor in [GM, SECOND_GM, VIEWER, AREA]:
                instance.run(f"insert into stabilis.test_location_grants values('{actor}','{LOCATION}');")
            yield instance
        finally:
            subprocess.run(control + ["-m", "immediate", "-w", "stop"], check=True, capture_output=True)


def test_server_math(db):
    def metrics(values):
        return db.run(f"select stabilis.labor_metrics({literal(json.dumps(values))}::jsonb)")
    assert metrics(INPUT) == dict(actual_pct=30, points_over=5, hours_over=10, schedule_effect=0,
                                  sales_effect=250, payroll_effect=200, total_over=450)
    sales_only = metrics(dict(INPUT, scheduled_cost=2500, actual_cost=2500, actual_hours=125))
    assert [sales_only[k] for k in ('schedule_effect','sales_effect','payroll_effect','total_over')] == [0,250,0,250]
    overbuilt = metrics(dict(NEXT, scheduled_cost=2700, actual_cost=2700))
    assert [overbuilt[k] for k in ('schedule_effect','sales_effect','payroll_effect','total_over')] == [200,0,0,200]
    incomplete = metrics(dict(INPUT, forecast_sales=None, actual_sales=0))
    assert incomplete['actual_pct'] is None and incomplete['hours_over'] == 10
    assert incomplete['sales_effect'] is None and incomplete['schedule_effect'] is None


def create(db, week=WEEK):
    return db.save(ANALYST, "create", {"week_start": week,"inputs": INPUT,"source":"Matched location exports"})


def enroll(db):
    db.run(f"select public.stabilis_enroll_labor_assignee('{ORG}','{LOCATION}','Location GM')",actor=GM)


def assigned(db, week=WEEK):
    enroll(db)
    initial = create(db,week)
    released = db.save(ANALYST,"release",{"note":"Reviewed payroll and forecast"},initial)
    return db.save(OWNER,"assign",{"title":"Review closing hours","assignee_id":GM,
                                   "due_date":"2026-12-10","next_review":"2026-12-11"},released)


def test_permissions_and_draft_revisions(db):
    week = "2026-09-07"
    d = create(db,week)
    assert not any(r["id"]==d["id"] for r in db.read(OWNER))
    assert not any(r["id"]==d["id"] for r in db.read(GM))
    assert create(db,week)['id'] == d['id']
    db.save(ANALYST,"create",{"week_start":week,"inputs":NEXT,"source":"Corrected"},error="A review exists")
    revised = db.save(ANALYST,"revise",{"inputs":NEXT,"source":"Corrected paid hours"},d)
    assert revised["version"]==2 and revised["metrics"]["total_over"]==0
    db.save(VIEWER,"release",{"note":"review"},revised,error="Review unavailable")
    db.read(OUTSIDE,error="Location unavailable")
    db.read(GM,OTHER_LOCATION,error="Location unavailable")
    db.read(OWNER,OUTSIDE_LOCATION,error="Location unavailable")
    db.read(None,role="anon",error="permission denied")
    db.run("select * from stabilis.weekly_labor_reviews",actor=GM,error="permission denied")


def test_review_and_retries(db):
    row = assigned(db)
    assert row['status']=='assigned' and row['verification'] is None
    db.save(SECOND_GM,'accept',{},row,error='Assigned GM')
    changed = db.save(GM,'request_change',{'note':'Change the due date'},row)
    row = db.save(AREA,'assign',{'title':'Review closing hours','assignee_id':GM,
                                 'due_date':WEEK2,'next_review':WEEK2},changed)
    accepted = db.save(GM,'accept',{},row)
    assert db.save(GM,'accept',{},row)['version']==accepted['version']
    evidence = db.save(GM,'submit_evidence',{'note':'Signed closing schedule in folder A'},accepted)
    compared = db.save(ANALYST,'compare',{'week_start':WEEK2,'inputs':NEXT,'source':'Matched payroll',
                                          'comparable':True,'note':'Same fiscal days and rates'},evidence)
    assert compared['followup']['observed_change']==450 and compared['verification'] is None
    finance = dict(amount=200,finance_reference="Client finance approval 87",
                   attribution="Signed schedule effect after adjustments",overlap_check="Payroll only counted once")
    db.save(ANALYST,'verify',finance,compared,error='Client owner must record')
    db.save(OWNER,'verify',dict(finance,amount=451),compared,error='cannot exceed')
    verified = db.save(OWNER,'verify',finance,compared)
    assert verified['verification']['amount']==200
    reopened = db.save(OWNER,'reopen',{'note':'Recheck opening hours'},verified)
    assert reopened['status']=='accepted' and reopened['verification'] is None and reopened['followup'] is None
    assert db.run(f"select (previous_state->'verification'->>'amount')::numeric from stabilis.weekly_labor_audit "
                  f"where review_id='{verified['id']}' and version={reopened['version']}")==200


def test_incomparable_worse_and_concurrent_updates(db):
    row = assigned(db,"2026-10-19")

    def accept_or_change(op):
        try:
            return db.save(GM,op,{'note':'Manager response'},row)['status']
        except AssertionError as exc:
            assert 'Refresh before trying again' in str(exc)
            return 'stale'
    with ThreadPoolExecutor(max_workers=2) as threads:
        states = list(threads.map(accept_or_change,['accept','request_change']))
    assert states.count('stale')==1
    row = next(r for r in db.read(GM) if r['id']==row['id'])
    if row['status']=='change_requested':
        row = db.save(OWNER,'assign',{'title':'Review closing hours','assignee_id':GM,
                                      'due_date':'2026-10-26','next_review':'2026-10-26'},row)
        row = db.save(GM,'accept',{},row)
    row = db.save(GM,'submit_evidence',{'note':'Revised schedule posted'},row)
    follow = dict(week_start='2026-10-26', inputs=dict(INPUT,actual_cost=2800),source='Payroll',
                  comparable=False,note='Different opening hours')
    row = db.save(ANALYST,'compare',follow,row)
    assert row['followup']['observed_change'] is None
    row = db.save(ANALYST,'compare',dict(follow,comparable=True,note='Matched opening hours after review'),row)
    assert row['followup']['observed_change']==-100
    db.save(OWNER,'verify',{'amount':100},row,error='positive comparable change')
