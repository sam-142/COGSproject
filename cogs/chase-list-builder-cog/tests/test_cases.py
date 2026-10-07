"""One section per case folder in evaluation/fixtures/ (copied from sample-data/).
Each folder's README in sample-data/ says what it tests and what should happen."""
import filecmp
import json
import shutil
from pathlib import Path

import pytest

from chase_list import cli, core
from cog_transactions import load, shape

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evaluation" / "fixtures"
SAMPLE_DATA = ROOT.parents[1] / "sample-data"


def run(*files, **kw):
    return core.run([FIXTURES / f for f in files], **kw)


def chase(result, tx_id):
    return next(t for t in result["transactions"] if t["id"] == tx_id)["inferred"]["chase"]


def draft(result, tx_id):
    return next(d for d in result["drafts"] if d["transaction_id"] == tx_id)


# --- malformed ---------------------------------------------------------------

def test_bad_rows_dont_stop_the_run():
    result = run("malformed/bad-rows.csv")
    assert [t["id"] for t in result["transactions"]] == ["m_ok", "m_refund"]
    assert result["run"]["counts"]["unparsed_rows"] == 5
    assert chase(result, "m_refund")["status"] == "skip"


def test_missing_column_stops_the_run():
    with pytest.raises(load.ExportError, match="missing column"):
        run("malformed/missing-column.csv")


def test_empty_export_drafts_nothing(tmp_path):
    result = run("malformed/header-only.csv")
    assert result["drafts"] == [] and result["run"]["period"] is None
    cli.main(["draft", str(FIXTURES / "malformed/header-only.csv"), "--no-log", "--out", str(tmp_path)])
    assert (tmp_path / "chase_empty.drafts.md").exists()


def test_empty_export_alongside_a_real_one_changes_nothing():
    alone = run("routing/export.csv")
    both = run("routing/export.csv", "malformed/header-only.csv")
    assert [t["id"] for t in both["transactions"]] == [t["id"] for t in alone["transactions"]]


# --- routing -----------------------------------------------------------------

def test_known_card_goes_to_its_channel():
    result = run("routing/export.csv")
    assert chase(result, "rt_known")["status"] == "draft"
    assert draft(result, "rt_known")["channel"] == "#card-1290"


@pytest.mark.parametrize("tx_id", ["rt_unknown_card", "rt_no_card"])
def test_unknown_or_missing_card_needs_routing(tx_id):
    result = run("routing/export.csv")
    assert chase(result, tx_id)["status"] == "needs-routing"
    d = draft(result, tx_id)
    assert d["channel"] is None and d["needs_routing"]


def test_missing_card_number_shows_as_unknown_in_the_draft():
    assert "card ending ????" in draft(run("routing/export.csv"), "rt_no_card")["text"]


# --- receipts ----------------------------------------------------------------

@pytest.mark.parametrize("tx_id, asks", [
    ("rc_none", ["purpose", "department", "receipt"]),
    ("rc_receipt_only", ["purpose", "department"]),
    ("rc_receipt_and_memo", ["purpose", "department"]),
    ("rc_memo_only", ["purpose", "department", "receipt"]),
])
def test_receipt_question_only_when_no_receipt(tx_id, asks):
    assert chase(run("receipts/export.csv"), tx_id)["ask_for"] == asks


def test_policy_can_skip_charges_with_receipt_and_memo(tmp_path):
    ctx = tmp_path / "context"
    shutil.copytree(ROOT / "context", ctx)
    policy = ctx / "chase-policy.yaml"
    policy.write_text(policy.read_text().replace("skip_when_receipt_and_memo: false",
                                                 "skip_when_receipt_and_memo: true"))
    result = run("receipts/export.csv", context_dir=ctx)
    assert chase(result, "rc_receipt_and_memo")["status"] == "skip"
    for tx_id in ("rc_none", "rc_receipt_only", "rc_memo_only"):   # need both to be skipped
        assert chase(result, tx_id)["status"] == "draft"


# --- matching ----------------------------------------------------------------

EARLY, LATE = "matching/export-2026-09-13.csv", "matching/export-2026-09-16.csv"


def test_two_visits_each_match_their_own_pending_charge():
    result = run(EARLY, LATE)
    assert {(s["pending_id"], s["replaced_by"], s["how"]) for s in result["superseded"]} == {
        ("mt_px_a", "mt_tx_a", "match"),
        ("mt_px_b", "mt_tx_b", "match"),
        ("mt_px_other_card", "mt_tx_other_card", "export"),
    }


def test_same_merchant_on_another_card_is_not_matched():
    result = run(EARLY, LATE)
    tx = next(t for t in result["transactions"] if t["id"] == "mt_tx_other_card")
    assert "pending_match" not in tx["inferred"]          # linked by the export, not guessed


def test_hold_that_never_posts_stays_pending_and_is_chased():
    result = run(EARLY, LATE)
    assert chase(result, "mt_px_hold")["status"] == "draft"


def test_matched_charges_are_named_in_a_warning():
    warnings = " ".join(run(EARLY, LATE)["run"]["warnings"])
    assert "mt_tx_a" in warnings and "mt_tx_b" in warnings


def test_chased_while_pending_is_not_chased_again_once_posted(tmp_path):
    log_path = tmp_path / "log.json"
    first = run(EARLY, log_path=log_path)
    saved = tmp_path / "first.chase.json"
    saved.write_text(json.dumps(first, default=shape.to_json))
    cli.main(["sent", str(saved), "--log", str(log_path)])

    second = run(LATE, log_path=log_path)
    assert {t["id"]: chase(second, t["id"])["status"] for t in second["transactions"]} == {
        "mt_tx_a": "already-chased", "mt_tx_b": "already-chased", "mt_tx_other_card": "already-chased"}
    assert second["drafts"] == []


# --- slack-safety ------------------------------------------------------------

@pytest.mark.parametrize("tx_id", ["ss_here", "ss_channel", "ss_backticks"])
def test_descriptor_cant_ping_or_break_formatting(tx_id):
    text = draft(run("slack-safety/export.csv"), tx_id)["text"]
    merchant_line = next(line for line in text.splitlines() if line.startswith(">"))
    assert "@" not in merchant_line and "<!" not in merchant_line and "`" not in merchant_line


def test_cardholder_name_cant_ping_either(tmp_path):
    template = tmp_path / "t.md"
    template.write_text("Card holder: {cardholder}\n")
    text = draft(run("slack-safety/export.csv", template_path=template), "ss_holder")["text"]
    assert text == "Card holder: (at)everyone\n"


# --- the copies match sample-data/ -------------------------------------------

@pytest.mark.skipif(not SAMPLE_DATA.exists(), reason="sample-data/ not alongside this Cog")
@pytest.mark.parametrize("path", sorted(p.relative_to(FIXTURES) for p in FIXTURES.rglob("*.csv")),
                         ids=str)
def test_fixture_matches_sample_data(path):
    assert filecmp.cmp(FIXTURES / path, SAMPLE_DATA / path, shallow=False), \
        f"{path} differs from sample-data/{path}; change sample-data, then copy it here"
