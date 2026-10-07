"""One section per case folder in evaluation/fixtures/ (copied from sample-data/).
Each folder's README in sample-data/ says what it tests and what should happen.

Tests marked xfail are known gaps: they assert what *should* happen, fail
today, and will start passing (and so fail the run, being strict) once fixed.
"""
import filecmp
from pathlib import Path

import pytest

from auto_coder import core
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
    txs, bad = load.load_csv(FIXTURES / "malformed" / "bad-rows.csv")
    assert [t["id"] for t in txs] == ["m_ok", "m_refund"]
    reasons = {b["row"]: b["reason"] for b in bad}
    assert reasons[4] == "empty required field(s): amount"
    assert "13" in reasons[5]                                  # month 13
    assert "settled" in reasons[6]
    assert "twelve" in reasons[7]


def test_money_formatted_amount_is_not_parsed_yet():
    # "$1,234.56" is rejected. If the real Brex export formats amounts like this,
    # load.py must learn to read it; until then the row is listed as unparsed.
    _, bad = load.load_csv(FIXTURES / "malformed" / "bad-rows.csv")
    assert any("$1,234.56" in b["reason"] for b in bad)


def test_missing_column_stops_the_run():
    with pytest.raises(load.ExportError, match="missing column"):
        load.load_csv(FIXTURES / "malformed" / "missing-column.csv")


def test_excel_style_file_with_bom_reads():
    txs, bad = load.load_csv(FIXTURES / "malformed" / "excel-bom.csv")
    assert [t["id"] for t in txs] == ["m_bom"] and bad == []


def test_empty_export_runs_cleanly():
    result = core.run(FIXTURES / "malformed" / "header-only.csv")
    assert result["transactions"] == [] and result["run"]["abstention_rate"] is None


# --- subscription-changes ----------------------------------------------------

CHANGES = ("month-2026-09.csv", ["history-2026-07.csv", "history-2026-08.csv"])


@pytest.fixture(scope="module")
def changes():
    return run("subscription-changes", *CHANGES)


@pytest.mark.parametrize("tx_id, expected", [
    ("sc_09_figma", ("recurring", "proposed")),          # +8%, within tolerance
    ("sc_09_notion", ("amount-changed", "needs-human")),  # +15%
    ("sc_09_zoom", ("amount-changed", "needs-human")),    # -50%, a downgrade
    ("sc_09_hubspot", ("recurring", "proposed")),         # unchanged
    ("sc_09_datadog", ("recurring", "proposed")),         # usage-billed, drifting both ways
    ("sc_09_linear", ("recurring", "proposed")),          # moved from card 8823 to 4417
])
def test_subscription_changes(changes, tx_id, expected):
    assert outcome(changes, tx_id) == expected


# --- long-history ------------------------------------------------------------

LONG = ("month-2026-09.csv", [f"history-2026-{m:02d}.csv" for m in range(3, 9)])


@pytest.fixture(scope="module")
def long_history():
    return run("long-history", *LONG)


def test_six_months_of_history_is_recurring(long_history):
    assert outcome(long_history, "lh_09_github") == ("recurring", "proposed")


def test_subscription_that_stopped_last_month_is_missing(long_history):
    assert "miro" in missing(long_history)


@pytest.mark.xfail(strict=True, reason="known gap: expected-but-missing never forgets a vendor")
def test_subscription_cancelled_months_ago_is_not_missing(long_history):
    assert "loom" not in missing(long_history)


# --- double-charge -----------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="known gap: identical charges in one month are both coded")
def test_second_identical_charge_is_flagged():
    result = run("double-charge", "month-2026-09.csv", ["history-2026-07.csv", "history-2026-08.csv"])
    statuses = sorted(outcome(result, t)[1] for t in ("dc_09_figma_a", "dc_09_figma_b"))
    assert statuses == ["needs-human", "proposed"]


# --- history-order -----------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="known gap: a later month passed as history counts as evidence")
def test_later_month_is_not_used_as_history():
    result = run("history-order", "month-2026-08.csv", ["history-2026-07.csv", "later-2026-09.csv"])
    assert outcome(result, "ho_08_canva")[0] == "new"


# --- the copies match sample-data/ -------------------------------------------

@pytest.mark.skipif(not SAMPLE_DATA.exists(), reason="sample-data/ not alongside this Cog")
@pytest.mark.parametrize("path", sorted(p.relative_to(FIXTURES) for p in FIXTURES.rglob("*.csv")),
                         ids=str)
def test_fixture_matches_sample_data(path):
    assert filecmp.cmp(FIXTURES / path, SAMPLE_DATA / path, shallow=False), \
        f"{path} differs from sample-data/{path}; change sample-data, then copy it here"
