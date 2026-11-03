"""The web page, driven over real HTTP the way the page does it, with both Cogs
run for real (through pixi) on their synthetic test data."""
import csv
import io
import json
import shutil
import sys
import threading
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import server  # noqa: E402

COGS = APP.parent / "cogs"
AUTO = COGS / "recurring-subscription-auto-coder-cog"
FIXTURES = AUTO / "evaluation" / "fixtures"
MONTH = FIXTURES / "baseline" / "brex-transactions-2026-09.csv"
HISTORY = [FIXTURES / "baseline" / f"brex-transactions-2026-0{m}.csv" for m in (7, 8)]


@pytest.fixture(scope="module")
def context_dir(tmp_path_factory):
    """Both Cogs' synthetic test context in one folder, as a real override folder would be."""
    folder = tmp_path_factory.mktemp("context")
    for cog in ("recurring-subscription-auto-coder-cog", "chase-list-builder-cog"):
        for f in (COGS / cog / "evaluation" / "fixtures" / "context").glob("*.yaml"):
            shutil.copy(f, folder / f.name)
    return folder


@pytest.fixture()
def server_url(tmp_path, context_dir):
    app = server.App(context_dir=context_dir, workdir=tmp_path / "work")
    srv = server.serve(app, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield app, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()
    app.close()


def post(base, fields, token):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for field, name, data in fields:
        body.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
                   f"filename=\"{name}\"\r\nContent-Type: text/csv\r\n\r\n".encode() + data + b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(f"{base}/run", data=body.getvalue(), method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}", "X-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def fields():
    return [("statement", MONTH.name, MONTH.read_bytes())] + [("history", h.name, h.read_bytes()) for h in HISTORY]


@pytest.fixture()
def result(server_url):
    app, base = server_url
    status, data = post(base, fields(), app.token)
    assert status == 200, data
    return app, base, data


def test_the_app_contains_no_cog_code():
    source = (APP / "server.py").read_text()
    assert "import auto_coder" not in source and "import chase_list" not in source
    assert "cog_transactions" not in source


def test_page_is_served_and_loads_nothing_external(server_url):
    app, base = server_url
    status, headers, body = get(base + "/")
    page = body.decode()
    assert status == 200 and app.token in page
    assert "https://" not in page and "http://" not in page
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_one_run_gives_the_updated_statement_the_report_and_the_drafts(result):
    app, base, data = result
    c = data["counts"]
    assert (c["transactions"], c["memos"], c["drafts"], c["needs_routing"]) == (51, 31, 15, 0)
    assert c["history_months"] == ["2026-07", "2026-08"]
    main = [d["name"] for d in data["downloads"] if d["main"]]
    assert main == ["brex-transactions-2026-09.upload.csv", "brex-transactions-2026-09.recurring-review.csv",
                    "chase_2026-09-01_to_2026-09-30.drafts.md"]

    status, headers, body = get(f"{base}/download/{data['run']}/{main[0]}?token={app.token}")
    assert status == 200 and "attachment" in headers["Content-Disposition"]
    rows = {r["Id"]: r for r in csv.DictReader(io.StringIO(body.decode("utf-8-sig")))}
    assert rows["tx_0901a"]["Memo"] == "GITHUB.COM 4ZK8M Paid by OT, Serving Engineering OT"


def test_drafts_are_for_charges_without_a_memo_only(result):
    _, _, data = result
    merchants = sorted(d["merchant"] for d in data["drafts"])
    assert "Delta Air Lines" in merchants and "Marriott" in merchants
    assert "GitHub" not in merchants and "Amazon Web Services" not in merchants
    delta = next(d for d in data["drafts"] if d["merchant"] == "Delta Air Lines")
    assert delta["channel"] == "#card-1290" and "ref: tx_0910c" in delta["text"]


def test_flagged_subscriptions_and_missing_ones_are_shown(result):
    _, _, data = result
    assert any(f["merchant"] == "Grafana Labs" and f["note"].startswith("new:") for f in data["flagged"])
    assert data["missing"] == ["loom"]
    assert any(w.startswith("Auto-coder:") for w in data["warnings"])


def test_requests_without_the_token_are_refused(result):
    app, base, data = result
    assert post(base, fields(), "wrong")[0] == 403
    assert get(f"{base}/download/{data['run']}/{data['downloads'][0]['name']}?token=wrong")[0] == 403


def test_only_files_from_a_run_can_be_downloaded(result):
    app, base, data = result
    for name in ("..%2Finputs%2Fbrex-transactions-2026-09.csv", "nope.csv"):
        assert get(f"{base}/download/{data['run']}/{name}?token={app.token}")[0] == 404


def test_bad_uploads_are_explained(server_url):
    app, base = server_url
    status, data = post(base, [("statement", "notes.txt", b"hello")], app.token)
    assert status == 400 and "isn't a CSV" in data["error"]
    status, data = post(base, [("statement", "a.csv", MONTH.read_bytes()), ("statement", "b.csv", MONTH.read_bytes())], app.token)
    assert status == 400 and "exactly one statement" in data["error"]
    bad = (FIXTURES / "malformed" / "missing-column.csv").read_bytes()
    status, data = post(base, [("statement", "m.csv", bad)], app.token)
    assert status == 400 and "missing column" in data["error"]      # the Cog's own error line


def test_uploads_and_results_are_deleted_when_it_stops(tmp_path, context_dir):
    app = server.App(context_dir=context_dir, workdir=tmp_path / "work")
    app.run((MONTH.name, MONTH.read_bytes()), [])
    assert any(app.workdir.rglob("*.upload.csv")) and any(app.workdir.rglob("*.drafts.md"))
    app.close()
    assert not app.workdir.exists()


def test_drafts_show_the_cardholder(result):
    _, _, data = result
    delta = next(d for d in data["drafts"] if d["merchant"] == "Delta Air Lines")
    assert delta["cardholder"] == "Alex Rivera"
    assert delta["text"].startswith("A charge on the card ending 1290 (Alex Rivera)")
