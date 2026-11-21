"""Exercise actual Supabase services with fictional files in a disposable loopback environment."""

from __future__ import annotations

import base64
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DOCKER = ("docker", "--host=unix:///var/run/docker.sock")
BUCKET = "stabilis-raw"
WEEK = "2026-10-26"
FOLLOWING_WEEK = "2026-11-02"
BASELINE = {
    "forecast_sales": 10000,
    "actual_sales": 9000,
    "target_pct": 25,
    "scheduled_hours": 125,
    "actual_hours": 135,
    "scheduled_cost": 2500,
    "actual_cost": 2700,
}
DENIED = (400, 401, 403, 404)
BASELINE_MIGRATION = ROOT / "supabase/migrations/20261120220000_weekly_labor_review.sql"
ARCHIVE_MIGRATION = ROOT / "supabase/migrations/20261120231842_weekly_labor_source_archive.sql"
FOUNDATION = ROOT / "tests/labor/foundation.sql"
IMAGES = {
    "storage": "supabase/storage-api:v1.98.5",
    "auth": "supabase/gotrue:v2.187.0",
    "rest": "postgrest/postgrest:v14.0",
}
ORG, LOCATION, OTHER_ORG, OTHER_LOCATION = [f"00000000-0000-0000-0000-{value:012d}" for value in (100, 101, 102, 103)]
FILE = (ROOT.parent / "assets/labor-examples/payroll.csv").read_bytes()
LEGACY = b"report,status\nfictional,retained\n"


def command(*args, input_text=None, env=None):
    result = subprocess.run(args, input=input_text, capture_output=True, text=True, env=env)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr.strip()}")
    return result.stdout


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def token(secret, role):
    def b64(value):
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    header = b64(b'{"alg":"HS256","typ":"JWT"}')
    payload = b64(json.dumps({"role": role, "exp": int(time.time()) + 900}).encode())
    message = f"{header}.{payload}"
    return f"{message}.{b64(hmac.digest(secret.encode(), message.encode(), 'sha256'))}"


def http(method, url, *, bearer=None, payload=None, content=None):
    headers = {"Authorization": "Bearer " + bearer} if bearer else {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
        content = json.dumps(payload).encode()
    elif content is not None:
        headers.update({"Content-Type": "text/csv", "x-upsert": "false"})
    request = Request(url, headers=headers, data=content, method=method)
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.read()


def checked(label, result, codes=(200, 201, 204)):
    status, body = result
    if status not in codes:
        raise RuntimeError(f"{label} failed with HTTP {status}: {body.decode(errors='replace')[:400]}")
    print(f"{label}: HTTP {status}", flush=True)
    return body


def healthy(url):
    expires = time.monotonic() + 25
    while time.monotonic() < expires:
        try:
            if http("GET", url)[0] < 500:
                return
        except (TimeoutError, URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Local service failed to start: {url}")


def launch(service, name, settings):
    arguments = [arg for key, value in settings.items() for arg in ("-e", f"{key}={value}")]
    command(*DOCKER, "run", "--rm", "--detach", "--network", "host", "--name", name, *arguments, IMAGES[service])


def port_url(port):
    return f"http://127.0.0.1:{port}"


def rehearse_review(sql, auth, rpc, actors, draft):
    analyst = actors["analyst"]["access_token"]
    owner = actors["owner"]["access_token"]
    manager = actors["manager"]
    assigned = manager["access_token"]
    other_manager = actors["other_manager"]["access_token"]
    viewer = actors["viewer"]["access_token"]
    outsider = actors["outsider"]["access_token"]

    def save(row, action, actor, payload=None, codes=(200,), label=None):
        return rpc(
            "stabilis_save_labor_review",
            {"p_review_id": row["id"], "p_version": row["version"], "p_operation": action, "p_payload": payload or {}},
            actor,
            codes,
            label or action,
        )

    assert rpc("stabilis_labor_reviews", {}, owner, label="Owner reads no unreleased draft") == []
    rpc("stabilis_labor_reviews", {}, outsider, DENIED, "Deny cross-tenant review")
    rpc("stabilis_enroll_labor_assignee", {"p_name": "Synthetic GM"}, assigned)
    released = save(draft, "release", analyst, {"note": "Checked record arithmetic, coverage and allocation."})
    assigned_row = save(
        released,
        "assign",
        owner,
        {
            "title": "Check closing coverage",
            "assignee_id": manager["id"],
            "due_date": "2026-11-05",
            "next_review": "2026-11-09",
            "target_measure": "At most 125 paid hours",
            "evidence_required": "Daily scheduled and actual closing punch totals",
        },
    )
    save(assigned_row, "accept", other_manager, codes=DENIED, label="Deny unassigned GM acceptance")
    accepted = save(assigned_row, "accept", assigned)
    assert save(assigned_row, "accept", assigned, label="Repeat the same acceptance")["version"] == accepted["version"]
    evidence = save(
        accepted, "submit_evidence", assigned, {"note": "Synthetic closing schedules and paid hours reconciled."}
    )
    compared = save(
        evidence,
        "compare",
        owner,
        {
            "week_start": FOLLOWING_WEEK,
            "source": "Synthetic matched week export",
            "comparable": True,
            "inputs": {**BASELINE, "actual_sales": 9500, "actual_hours": 125, "actual_cost": 2500},
            "note": "Operating hours, role mix and wage rates comparable.",
        },
    )
    assert compared["followup"]["metrics"]["total_over"] == 125 and compared["followup"]["observed_change"] == 325
    finance = {
        "amount": 150,
        "finance_reference": "Synthetic finance approval",
        "attribution": "Closing coverage checked after sales adjustment",
        "overlap_check": "No other credit",
    }
    save(compared, "verify", viewer, finance, DENIED, "Deny read-only finance validation")
    verified = save(compared, "verify", owner, finance)
    assert verified["verification"]["amount"] == 150
    assert rpc("stabilis_labor_reviews", {}, owner)[0]["id"] == verified["id"]
    sql(
        f"delete from stabilis.membership_locations where membership_id in "
        f"(select id from stabilis.memberships where profile_id='{manager['id']}');"
    )
    rpc("stabilis_labor_reviews", {}, assigned, DENIED, "Deny review after location grant revoked")
    save(
        verified,
        "submit_evidence",
        assigned,
        {"note": "Further evidence"},
        DENIED,
        "Deny mutation after location grant revoked",
    )
    checked("Revoke GM Auth session", http("POST", auth + "/logout?scope=local", bearer=assigned), (204,))
    checked(
        "Deny refresh after Auth logout",
        http("POST", auth + "/token?grant_type=refresh_token", payload={"refresh_token": manager["refresh_token"]}),
        DENIED,
    )


def rehearsal(sql, auth, rest, storage, storage_container, secret):
    admin = token(secret, "service_role")
    anon = token(secret, "anon")
    actors = {}
    members = {
        "analyst": ("STABILIS_ANALYST", ORG, False),
        "owner": ("OWNER_EXECUTIVE", ORG, False),
        "manager": ("GENERAL_MANAGER", ORG, True),
        "other_manager": ("GENERAL_MANAGER", ORG, True),
        "viewer": ("READ_ONLY", ORG, True),
        "outsider": ("STABILIS_ANALYST", OTHER_ORG, False),
    }
    for name, (role, organization, location_grant) in members.items():
        email = secrets.token_hex(8) + "@fixture.invalid"
        password = secrets.token_urlsafe(24)
        user = json.loads(
            checked(
                "Create confirmed " + name,
                http(
                    "POST",
                    auth + "/admin/users",
                    bearer=admin,
                    payload={"email": email, "password": password, "email_confirm": True},
                ),
            )
        )
        uid = user["id"]
        sql(
            f"insert into stabilis.profiles values ('{uid}'); "
            f"insert into stabilis.memberships(organization_id,profile_id,role,status) values ('{organization}','{uid}','{role}','ACTIVE');"
        )
        if location_grant:
            sql(
                f"insert into stabilis.membership_locations "
                f"select id,'{LOCATION}' from stabilis.memberships where profile_id='{uid}';"
            )
        credentials = json.loads(
            checked(
                "Authenticate " + name,
                http("POST", auth + "/token?grant_type=password", payload={"email": email, "password": password}),
            )
        )
        actors[name] = {"id": uid, **credentials}
    analyst, owner, outsider = (actors[name]["access_token"] for name in ("analyst", "owner", "outsider"))
    scope = {"p_organization_id": ORG, "p_location_id": LOCATION}

    def rpc(name, payload, actor=analyst, codes=(200, 204), label=None):
        body = checked(
            label or name, http("POST", rest + "/rpc/" + name, bearer=actor, payload={**scope, **payload}), codes
        )
        return json.loads(body) if body else None

    digest = sha256(FILE).hexdigest()
    registration = {
        "p_week_start": WEEK,
        "p_filename": "synthetic-payroll.csv",
        "p_sha256": digest,
        "p_size_bytes": len(FILE),
        "p_retain_through": "2099-01-01",
    }
    entry = rpc("stabilis_prepare_weekly_source", registration)
    assert rpc("stabilis_prepare_weekly_source", registration) == entry
    upload = storage + "/object/" + BUCKET + "/" + entry["path"]
    download = storage + "/object/authenticated/" + BUCKET + "/" + entry["path"]
    checked(
        "Deny analyst signed upload",
        http("POST", storage + "/object/upload/sign/" + BUCKET + "/" + entry["path"], bearer=analyst, payload={}),
        DENIED,
    )
    checked("Deny owner raw upload", http("POST", upload, bearer=owner, content=FILE), DENIED)
    checked("Upload pending original", http("POST", upload, bearer=analyst, content=FILE))
    checked("Deny download before finalize", http("GET", download, bearer=analyst), DENIED)
    rpc("stabilis_finish_weekly_source", {"p_source_id": entry["id"]})
    assert checked("Download retained original", http("GET", download, bearer=analyst)) == FILE
    checked(
        "Deny analyst signed download",
        http(
            "POST", storage + "/object/sign/" + BUCKET + "/" + entry["path"], bearer=analyst, payload={"expiresIn": 300}
        ),
        DENIED,
    )
    for name, actor in (("owner", owner), ("other tenant analyst", outsider), ("anonymous", anon)):
        checked("Deny raw access for " + name, http("GET", download, bearer=actor), DENIED)
    checked("Deny finalized replacement", http("PUT", upload, bearer=analyst, content=FILE), DENIED)

    report = {
        "type": "payroll",
        "filename": "synthetic-payroll.csv",
        "sha256": digest,
        "sheet": "CSV",
        "header_row": 1,
        "source_location": "Juniper Café",
        "mapping": {
            "date": "Business date",
            "role": "Role",
            "location": "Location",
            "actual_hours": "Paid hours",
            "actual_cost": "Paid labor cost",
        },
        "coverage": 7,
        "row_count": 14,
        "totals": {"actual_hours": 135, "actual_cost": 2700},
        "groups": [
            {"role": "Kitchen", "actual_hours": 66, "actual_cost": 1320},
            {"role": "Counter", "actual_hours": 69, "actual_cost": 1380},
        ],
        "gaps": [],
        "archive_id": entry["id"],
    }
    saved = rpc(
        "stabilis_save_labor_review",
        {
            "p_review_id": None,
            "p_version": 0,
            "p_operation": "create",
            "p_payload": {
                "week_start": WEEK,
                "source": "Synthetic sources",
                "inputs": BASELINE,
                "imports": [report],
            },
        },
    )
    assert saved["metrics"]["total_over"] == 450
    assert saved["metrics"]["sales_effect"] == 250 and saved["metrics"]["payroll_effect"] == 200
    rehearse_review(sql, auth, rpc, actors, saved)
    history_args = {"p_review_id": saved["id"]}

    def original_report():
        history = rpc("stabilis_weekly_source_history", history_args)
        baseline = next(version for version in history if version["operation"] == "create")
        return baseline["reports"][0]

    assert original_report()["archive"]["path"] == entry["path"]
    rpc("stabilis_weekly_source_history", history_args, owner, DENIED)

    legacy_path = ORG + "/legacy-control.csv"
    checked(
        "Place unrelated synthetic original",
        http("POST", storage + "/object/" + BUCKET + "/" + legacy_path, bearer=admin, content=LEGACY),
    )
    physical_before = command(*DOCKER, "exec", storage_container, "find", "/var/lib/storage", "-type", "f").splitlines()
    assert len(physical_before) == 2, physical_before
    sql(f"update stabilis.weekly_labor_source_files set retain_through='2026-11-03' where id='{entry['id']}';")
    checked("Deny expired download before physical removal", http("GET", download, bearer=analyst), DENIED)
    assert original_report()["archive"]["path"] is None
    deletion = json.loads(
        checked(
            "Delete expired original through private Storage API",
            http("DELETE", storage + "/object/" + BUCKET, bearer=admin, payload={"prefixes": [entry["path"]]}),
        )
    )
    assert [obj["name"] for obj in deletion] == [entry["path"]]
    checked("Original absent from Storage API", http("GET", download, bearer=admin), DENIED)
    assert (
        sql(f"select count(*) from storage.objects where bucket_id='{BUCKET}' and name='{entry['path']}';").strip()
        == "0"
    )
    physical_after = command(*DOCKER, "exec", storage_container, "find", "/var/lib/storage", "-type", "f").splitlines()
    assert len(physical_after) == 1 and "legacy-control.csv" in physical_after[0], physical_after
    assert (
        checked(
            "Unrelated original remains",
            http("GET", storage + "/object/authenticated/" + BUCKET + "/" + legacy_path, bearer=admin),
        )
        == LEGACY
    )
    final_report = original_report()
    assert final_report["sha256"] == digest
    assert final_report["archive"]["path"] is None


def main():
    if not all(shutil.which(tool) for tool in ("docker", "initdb", "pg_ctl", "psql")):
        raise SystemExit("Docker and PostgreSQL server binaries must be on PATH.")
    for image in IMAGES.values():
        command(*DOCKER, "image", "inspect", image)
    prefix = "stabilis-storage-qa-" + secrets.token_hex(5)
    names = {service: prefix + "-" + service for service in IMAGES}
    db_port, storage_port, auth_port, rest_port = (available_port() for _ in range(4))
    secret, password = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db_url = f"postgres://postgres:{password}@127.0.0.1:{db_port}/postgres"
    auth_url, rest_url, storage_url = map(port_url, (auth_port, rest_port, storage_port))

    with tempfile.TemporaryDirectory(prefix=prefix + "-") as directory:
        root = Path(directory)
        data, password_file = root / "pg", root / "pw"
        password_file.write_text(password)
        password_file.chmod(0o600)
        command(
            "initdb",
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
        )
        control = ["pg_ctl", "-D", str(data)]
        command(
            *control,
            "-w",
            "-l",
            str(root / "postgres.log"),
            "-o",
            f"-h 127.0.0.1 -p {db_port} -c unix_socket_directories=''",
            "start",
        )

        def sql(statement):
            return command(
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-qAt",
                "-h",
                "127.0.0.1",
                "-p",
                str(db_port),
                "-U",
                "postgres",
                "-d",
                "postgres",
                input_text=statement,
                env={**os.environ, "PGPASSWORD": password},
            )

        try:
            tenant_sql = FOUNDATION.read_text().split("create table stabilis.organizations", 1)[1]
            sql(
                """create schema auth; create schema stabilis;
              create function auth.uid() returns uuid language sql stable as
              $$ select coalesce(nullif(current_setting('request.jwt.claim.sub',true),''),
                 nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid $$;
              create table stabilis.organizations"""
                + tenant_sql
            )
            sql(
                f"insert into stabilis.organizations values ('{ORG}'),('{OTHER_ORG}'); "
                f"insert into stabilis.locations(id,organization_id) values ('{LOCATION}','{ORG}'),('{OTHER_LOCATION}','{OTHER_ORG}');"
            )
            launch(
                "storage",
                names["storage"],
                {
                    "SERVER_HOST": "127.0.0.1",
                    "SERVER_PORT": str(storage_port),
                    "AUTH_JWT_SECRET": secret,
                    "AUTH_JWT_ALGORITHM": "HS256",
                    "DATABASE_URL": db_url,
                    "DB_INSTALL_ROLES": "true",
                    "STORAGE_BACKEND": "file",
                    "FILE_STORAGE_BACKEND_PATH": "/var/lib/storage",
                    "STORAGE_S3_BUCKET": "fixture",
                    "SERVER_REGION": "local",
                    "UPLOAD_FILE_SIZE_LIMIT": "5242880",
                },
            )
            healthy(storage_url + "/status")
            checked(
                "Create synthetic private bucket",
                http(
                    "POST",
                    storage_url + "/bucket",
                    bearer=token(secret, "service_role"),
                    payload={"id": BUCKET, "name": BUCKET, "public": False},
                ),
            )
            sql(BASELINE_MIGRATION.read_text())
            sql(ARCHIVE_MIGRATION.read_text())
            launch(
                "auth",
                names["auth"],
                {
                    "GOTRUE_API_HOST": "127.0.0.1",
                    "GOTRUE_API_PORT": str(auth_port),
                    "API_EXTERNAL_URL": auth_url,
                    "GOTRUE_DB_DRIVER": "postgres",
                    "GOTRUE_DB_DATABASE_URL": db_url + "?sslmode=disable&search_path=auth",
                    "GOTRUE_DB_NAMESPACE": "auth",
                    "GOTRUE_SITE_URL": auth_url,
                    "GOTRUE_JWT_SECRET": secret,
                    "GOTRUE_JWT_ADMIN_ROLES": "service_role",
                    "GOTRUE_JWT_AUD": "authenticated",
                    "GOTRUE_JWT_DEFAULT_GROUP_NAME": "authenticated",
                    "GOTRUE_EXTERNAL_EMAIL_ENABLED": "true",
                    "GOTRUE_MAILER_AUTOCONFIRM": "true",
                },
            )
            healthy(auth_url + "/health")
            launch(
                "rest",
                names["rest"],
                {
                    "PGRST_SERVER_HOST": "127.0.0.1",
                    "PGRST_SERVER_PORT": str(rest_port),
                    "PGRST_DB_URI": db_url,
                    "PGRST_DB_SCHEMAS": "public",
                    "PGRST_DB_ANON_ROLE": "anon",
                    "PGRST_JWT_SECRET": secret,
                },
            )
            healthy(rest_url + "/")
            rehearsal(sql, auth_url, rest_url, storage_url, names["storage"], secret)
            print("Passed actual loopback Auth, PostgREST, Storage and physical deletion.", flush=True)
        except Exception:
            for name in names.values():
                logs = subprocess.run([*DOCKER, "logs", "--tail", "8", name], capture_output=True, text=True)
                if logs.returncode == 0:
                    print(logs.stdout)
                    print(logs.stderr)
            raise
        finally:
            subprocess.run([*DOCKER, "rm", "-f", *names.values()], capture_output=True)
            command(*control, "-m", "immediate", "-w", "stop")


if __name__ == "__main__":
    main()
