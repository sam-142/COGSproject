"""One section per case folder in evaluation/fixtures/ (copied from sample-data/).
Each folder's README in sample-data/ says what it tests and what should happen.

Tests marked xfail are known gaps: they assert what *should* happen, fail
today, and will start passing (and so fail the run, being strict) once fixed.
"""
import csv
import filecmp
from pathlib import Path

import pytest

from auto_coder import context, core
from cog_transactions import load

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evaluation" / "fixtures"
SAMPLE_DATA = ROOT.parents[1] / "sample-data"


def run(case, month, history=()):
    return core.run(FIXTURES / case / month, [FIXTURES / case / h for h in history])


def outcome(result, tx_id):
    tx = next(t for t in result["transactions"] if t["id"] == tx_id)
    return tx["inferred"]["recurrence"]["label"], tx["inferred"]["coding"]["status"]


def missing(result):
    return {m["vendor"] for m in result["expected_but_missing"]}


# --- malformed ---------------------------------------------------------------

def test_bad_rows_are_listed_with_a_reason_not_fatal():
    txs, bad, _ = load.load_csv(FIXTURES / "malformed" / "bad-rows.csv")
    assert [t["id"] for t in txs] == ["m_ok", "m_refund"]
    reasons = {b["row"]: b["reason"] for b in bad}
    assert reasons[4] == "empty required field(s): amount"
    assert "13/01/2026" in reasons[5]                          # day/month swapped
    assert "Settled" in reasons[6]                             # unknown Payment Status
    assert "twelve" in reasons[7]
    assert "2026-09-07" in reasons[9]                          # ISO, not MM/DD/YYYY


def test_money_formatted_amount_is_not_parsed_yet():
    # "$1,234.56" is rejected. If the real Brex export formats amounts like this,
    # load.py must learn to read it; until then the row is listed as unparsed.
    _, bad, _ = load.load_csv(FIXTURES / "malformed" / "bad-rows.csv")
    assert any("$1,234.56" in b["reason"] for b in bad)


def test_missing_column_stops_the_run():
    with pytest.raises(load.ExportError, match="missing column"):
        load.load_csv(FIXTURES / "malformed" / "missing-column.csv")


def test_excel_style_file_with_bom_reads():
    txs, bad, _ = load.load_csv(FIXTURES / "malformed" / "excel-bom.csv")
    assert [t["id"] for t in txs] == ["m_bom"] and bad == []


def test_only_the_required_columns_is_enough():
    txs, bad, columns = load.load_csv(FIXTURES / "malformed" / "required-columns-only.csv")
    assert [t["id"] for t in txs] == ["m_min"] and bad == []
    assert columns["read"] == 10 and columns["ignored"] == 0
    assert "Receipt URL" in columns["optional_missing"]
    assert txs[0]["parsed"]["receipt_attached"] is None      # unknown, not "no receipt"


def test_brex_export_is_trimmed_to_the_columns_we_use():
    txs, _, columns = load.load_csv(FIXTURES / "baseline" / "brex-transactions-2026-09.csv")
    assert columns == {"file": "brex-transactions-2026-09.csv", "read": 22, "ignored": 48,
                       "optional_missing": []}
    assert txs[0]["parsed"]["transaction_date"].isoformat() == "2026-09-01"   # from 09/01/2026


def test_declined_charge_is_never_coded():
    result = core.run(FIXTURES / "declined" / "export.csv")
    assert outcome(result, "dc_declined") == ("one-off", "not-included")
    tx = next(t for t in result["transactions"] if t["id"] == "dc_declined")
    assert tx["inferred"]["coding"]["reason"] == "declined charge"


def test_empty_export_runs_cleanly():
    result = core.run(FIXTURES / "malformed" / "header-only.csv")
    assert result["transactions"] == [] and result["run"]["abstention_rate"] is None


# --- subscription-changes ----------------------------------------------------

CHANGES = ("month-2026-09.csv", ["history-2026-07.csv", "history-2026-08.csv"])


@pytest.fixture(scope="module")
def changes():
    return run("subscription-changes", *CHANGES)


@pytest.mark.parametrize("tx_id, expected", [
    ("sc_09_figma", ("recurring", "ready")),             # +8%, within tolerance
    ("sc_09_notion", ("amount-changed", "ready")),        # +15%: entered, and flagged for review
    ("sc_09_zoom", ("amount-changed", "ready")),          # -50%, a downgrade
    ("sc_09_hubspot", ("recurring", "ready")),            # unchanged
    ("sc_09_datadog", ("recurring", "ready")),            # usage-billed, drifting both ways
    ("sc_09_linear", ("recurring", "ready")),             # moved from card 8823 to 4417
])
def test_subscription_changes(changes, tx_id, expected):
    assert outcome(changes, tx_id) == expected


# --- long-history ------------------------------------------------------------

LONG = ("month-2026-09.csv", [f"history-2026-{m:02d}.csv" for m in range(3, 9)])


@pytest.fixture(scope="module")
def long_history():
    return run("long-history", *LONG)


def test_six_months_of_history_is_recurring(long_history):
    assert outcome(long_history, "lh_09_github") == ("recurring", "ready")


def test_subscription_that_stopped_last_month_is_missing(long_history):
    assert "miro" in missing(long_history)


@pytest.mark.xfail(strict=True, reason="known gap: expected-but-missing never forgets a vendor")
def test_subscription_cancelled_months_ago_is_not_missing(long_history):
    assert "loom" not in missing(long_history)


# --- double-charge -----------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="known gap: identical charges in one month are both coded")
def test_second_identical_charge_is_flagged():
    result = run("double-charge", "month-2026-09.csv", ["history-2026-07.csv", "history-2026-08.csv"])
    flagged = sorted(bool(next(t for t in result["transactions"] if t["id"] == i)["inferred"]["coding"]["review"])
                     for i in ("dc_09_figma_a", "dc_09_figma_b"))
    assert flagged == [False, True]                      # the second one flagged as a possible duplicate


# --- history-order -----------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="known gap: a later month passed as history counts as evidence")
def test_later_month_is_not_used_as_history():
    result = run("history-order", "month-2026-08.csv", ["history-2026-07.csv", "later-2026-09.csv"])
    assert outcome(result, "ho_08_canva")[0] == "new"


# --- usage-billing -----------------------------------------------------------

USAGE = ("month-2026-09.csv", ["history-2026-07.csv", "history-2026-08.csv"])


@pytest.fixture(scope="module")
def usage():
    return run("usage-billing", *USAGE)


def recurrence(result, tx_id):
    return next(t for t in result["transactions"] if t["id"] == tx_id)["inferred"]["recurrence"]


def test_usage_billed_jump_is_coded_and_flagged(usage):
    # Datadog: 500 -> 520 -> 700. Usage-billed, so +35% is a flag, not a block.
    assert outcome(usage, "ub_09_datadog") == ("recurring", "ready")
    rec = recurrence(usage, "ub_09_datadog")
    assert rec["billing"] == "usage"
    assert rec["amount_flag"] == "amount up 34.6% on last charge (520.00)"
    coding = next(t for t in usage["transactions"] if t["id"] == "ub_09_datadog")["inferred"]["coding"]
    assert coding["review"] == rec["amount_flag"]
    assert rec["evidence"]["vs_last_charge"] == {"last_amount": 520.0, "month": "2026-08",
                                                  "change_percent": 34.6}


def test_fixed_price_jump_still_needs_a_person(usage):
    # Notion: 120 -> 120 -> 138, and the vendor list says fixed.
    assert outcome(usage, "ub_09_notion") == ("amount-changed", "ready")
    coding = next(t for t in usage["transactions"] if t["id"] == "ub_09_notion")["inferred"]["coding"]
    assert coding["review"].startswith("amount-changed:")
    assert "up 15% on last charge" in recurrence(usage, "ub_09_notion")["reason"]


def test_merchant_not_on_the_list_is_found_through_brex(usage):
    # Retool isn't on the vendor list; Brex says "Recurring software & SaaS".
    tx = next(t for t in usage["transactions"] if t["id"] == "ub_09_retool")
    assert tx["inferred"]["vendor"]["id"] == "retool" and tx["inferred"]["vendor"]["source"] == "export"
    assert outcome(usage, "ub_09_retool") == ("recurring", "ready")
    # No coding rule for it: the account comes from the Brex charge itself.
    assert tx["inferred"]["coding"]["from"]["ACCOUNT"] == "export"
    assert tx["inferred"]["recurrence"]["amount_flag"].startswith("amount up 54.1%")


def test_monthly_contractor_is_not_a_subscription(usage):
    # Same amount every month, but Brex's category isn't a subscription one.
    assert outcome(usage, "ub_09_contractor") == ("one-off", "not-included")


def test_vendor_sources_are_counted(usage):
    assert usage["run"]["counts"]["vendor_sources"] == {"context": 2, "export": 2}
    assert usage["run"]["counts"]["amount_flags"] == 2


def test_one_month_alone_gives_likely_recurring_not_new():
    result = run("usage-billing", "month-2026-09.csv")
    assert recurrence(result, "ub_09_retool")["label"] == "likely-recurring"
    assert recurrence(result, "ub_09_retool")["source"] == "export"
    assert "Brex categorises it as recurring software" in recurrence(result, "ub_09_retool")["reason"]
    assert recurrence(result, "ub_09_datadog")["label"] == "likely-recurring"
    assert outcome(result, "ub_09_contractor") == ("one-off", "not-included")


# --- an override folder replaces context files one by one --------------------

def test_override_folder_replaces_only_the_files_it_has(tmp_path):
    # A real vendor list, as tools/vendors_to_yaml.py writes it: names only.
    (tmp_path / "vendors.yaml").write_text(
        'status: real\nvendors:\n  - {name: "Datadog"}\n  - {name: "GitHub"}\n  - {name: "Uber", category: "travel"}\n')
    result = core.run(FIXTURES / "baseline" / "brex-transactions-2026-09.csv",
                      [FIXTURES / "baseline" / f"brex-transactions-2026-0{m}.csv" for m in (7, 8)],
                      context_dir=tmp_path)
    versions = result["run"]["context"]
    assert versions["vendors"] == {"version": "None", "status": "real", "from": "override"}
    assert versions["coding-rules"]["from"] == "default"
    vendor = lambda i: next(t for t in result["transactions"] if t["id"] == i)["inferred"]["vendor"]["id"]
    assert vendor("tx_0905a") == "datadog" and vendor("tx_0901a") == "github"
    # AWS isn't on this list, so Brex's Merchant Name stands in for it.
    aws = next(t for t in result["transactions"] if t["id"] == "tx_0901b")["inferred"]["vendor"]
    assert (aws["id"], aws["source"], aws["category"]) == ("amazon-web-services", "export", "subscription")
    assert outcome(result, "tx_0905a") == ("recurring", "ready")
    # The default (test) rule for datadog still applies: its account wins over Brex's.
    coding = next(t for t in result["transactions"] if t["id"] == "tx_0905a")["inferred"]["coding"]
    assert (coding["entry"]["ACCOUNT"], coding["from"]["ACCOUNT"]) == ("6120", "rule")


# --- dropped columns never reach an output ----------------------------------

# Values that only exist in columns the reader drops. None may appear anywhere
# in what the Cog writes.
DROPPED = ["fake-spender.example", "receipts.fake-brex.example", "dashboard.fake-brex.example",
           "Fake Approver", "Fake Attendee", "Fake Team Budget", "Fake Card Policy",
           "Liabilities:2100", "15:30:00"]


def test_dropped_columns_never_reach_an_output(tmp_path):
    from auto_coder import report
    result = run("baseline", "brex-transactions-2026-09.csv",
                 ["brex-transactions-2026-07.csv", "brex-transactions-2026-08.csv"])
    written = "".join(p.read_text() for p in report.write(result, tmp_path))
    written += report.summary(result)
    leaked = [v for v in DROPPED if v in written]
    assert not leaked, f"dropped columns leaked into the output: {leaked}"
    raw = (FIXTURES / "baseline" / "brex-transactions-2026-09.csv").read_text()
    assert all(v in raw for v in DROPPED), "the fixture should contain every dropped value"


# --- the copies match sample-data/ -------------------------------------------

@pytest.mark.skipif(not SAMPLE_DATA.exists(), reason="sample-data/ not alongside this Cog")
@pytest.mark.parametrize("path", sorted(p.relative_to(FIXTURES) for p in FIXTURES.rglob("*")
                                        if p.suffix in (".csv", ".yaml")), ids=str)
def test_fixture_matches_sample_data(path):
    assert filecmp.cmp(FIXTURES / path, SAMPLE_DATA / path, shallow=False), \
        f"{path} differs from sample-data/{path}; change sample-data, then copy it here"


# --- the command line --------------------------------------------------------

@pytest.mark.parametrize("args", [
    ["--history", "H7", "H8"],                  # one flag, several files
    ["--history", "H7", "--history", "H8"],     # the flag repeated
])
def test_every_history_file_given_is_used(args, tmp_path, capsys):
    from auto_coder import cli
    base = FIXTURES / "baseline"
    files = {"H7": str(base / "brex-transactions-2026-07.csv"), "H8": str(base / "brex-transactions-2026-08.csv")}
    cli.main(["code", str(base / "brex-transactions-2026-09.csv"), "--out", str(tmp_path)]
             + [files.get(a, a) for a in args])
    assert "history: 2 file(s), covering 2026-07, 2026-08" in capsys.readouterr().out


# --- a wrong --context fails instead of quietly using the defaults -----------

@pytest.mark.parametrize("make, message", [
    (lambda d: (d / "vendors.yaml").write_text("vendors: []\n") and d / "vendors.yaml", "takes a folder, not a file"),
    (lambda d: d / "nope", "folder not found"),
    (lambda d: (d / "notes.txt").write_text("x") and d, "has none of"),
])
def test_wrong_context_is_an_error(make, message, tmp_path):
    from auto_coder import context
    with pytest.raises(context.ContextError, match=message):
        context.load(make(tmp_path))


# --- the QuickBooks file ------------------------------------------------------

def test_quickbooks_file_has_exactly_the_quickbooks_columns(tmp_path):
    from auto_coder import report
    result = run("baseline", "brex-transactions-2026-09.csv",
                 ["brex-transactions-2026-07.csv", "brex-transactions-2026-08.csv"])
    qb_path = report.write(result, tmp_path)[0]
    rows = list(csv.reader(qb_path.open()))
    assert rows[0] == ["DATE", "REF NO.", "TYPE", "PAYEE", "ACCOUNT", "MEMO", "CLASS", "DEPARTMENT", "CHARGE"]
    assert len(rows) - 1 == result["run"]["counts"]["coding"]["ready"]
    first = dict(zip(rows[0], rows[1]))
    assert first["DATE"] == "09/01/2026" and first["TYPE"] == "Credit Card Expense"
    assert first["REF NO."] == "4417"                    # the card's last 4 digits


def test_ref_no_is_blank_without_a_card_number(tmp_path):
    src = FIXTURES / "baseline" / "brex-transactions-2026-09.csv"
    with src.open() as f, (tmp_path / src.name).open("w", newline="") as g:
        reader = csv.DictReader(f)
        writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            if row["Id"] == "tx_0901a":
                row["Last 4"] = ""
            writer.writerow(row)
    result = core.run(tmp_path / src.name, [FIXTURES / "baseline" / "brex-transactions-2026-08.csv"])
    coding = next(t for t in result["transactions"] if t["id"] == "tx_0901a")["inferred"]["coding"]
    assert coding["status"] == "ready" and coding["entry"]["REF NO."] == ""
    assert "REF NO." in coding["blank"]


def test_with_no_context_every_subscription_still_gets_an_entry(tmp_path, monkeypatch):
    # The Cog's own (empty) defaults: no vendor list, no rules. ACCOUNT comes from
    # Brex; CLASS and DEPARTMENT are blank; nothing is held back for that.
    monkeypatch.setattr(context, "DEFAULT_DIR", ROOT / "context")
    result = run("baseline", "brex-transactions-2026-09.csv",
                 ["brex-transactions-2026-07.csv", "brex-transactions-2026-08.csv"])
    entries = [t["inferred"]["coding"] for t in result["transactions"]
               if t["inferred"]["coding"]["status"] == "ready"]
    assert len(entries) == 32
    assert all(e["from"]["ACCOUNT"] == "export" and e["entry"]["ACCOUNT"] for e in entries)
    assert result["run"]["counts"]["blank_fields"]["CLASS"] == 32


def test_quickbooks_settings_can_be_overridden(tmp_path):
    (tmp_path / "quickbooks.yaml").write_text(
        'type_charge: "CC Expense"\nref_field: transaction_id\nref_max_length: 6\ndate_format: "%Y-%m-%d"\n')
    result = core.run(FIXTURES / "baseline" / "brex-transactions-2026-09.csv",
                      [FIXTURES / "baseline" / "brex-transactions-2026-07.csv"], context_dir=tmp_path)
    entry = next(t for t in result["transactions"] if t["id"] == "tx_0901a")["inferred"]["coding"]["entry"]
    assert (entry["TYPE"], entry["REF NO."], entry["DATE"]) == ("CC Expense", "_0901a", "2026-09-01")


# --- why each charge counts as a subscription ----------------------------------

def why(result, tx_id):
    return next(t for t in result["transactions"] if t["id"] == tx_id)["inferred"]["recurrence"]["why_subscription"]


def test_every_reason_that_applies_is_listed(usage):
    assert why(usage, "ub_09_datadog") == [
        "on the vendor list as a subscription, usage billing",
        "Brex category: Recurring software & SaaS",
        "charged in 2 earlier months (2026-07, 2026-08)",
    ]


def test_brex_only_subscription_says_so(usage):
    # Not on the vendor list: the evidence is Brex's category and the history.
    assert why(usage, "ub_09_retool") == [
        "Brex category: Recurring software & SaaS",
        "charged in 2 earlier months (2026-07, 2026-08)",
    ]


def test_fixed_price_shows_amount_matches(usage):
    assert "same amount (±10%) in 2 earlier months" not in why(usage, "ub_09_notion")   # +15%
    result = run("baseline", "brex-transactions-2026-09.csv",
                 ["brex-transactions-2026-07.csv", "brex-transactions-2026-08.csv"])
    assert "on the known-recurring list" in why(result, "tx_0901d")             # Google Workspace
    assert "same amount (±10%) in 2 earlier months" in why(result, "tx_0901d")


def test_one_month_alone_still_gives_reasons():
    assert why(run("usage-billing", "month-2026-09.csv"), "ub_09_retool") == [
        "Brex category: Recurring software & SaaS"]


def test_one_offs_have_no_subscription_reasons(usage, tmp_path):
    from auto_coder import report
    assert why(usage, "ub_09_contractor") == []
    rows = {r["transaction_id"]: r for r in csv.DictReader(report.write(usage, tmp_path)[1].open())}
    assert rows["ub_09_retool"]["reason"] == ("Brex category: Recurring software & SaaS; "
                                              "charged in 2 earlier months (2026-07, 2026-08)")
