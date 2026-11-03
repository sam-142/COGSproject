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
    assert result["run"]["counts"]["unparsed_rows"] == 6
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
def test_receipt_question_only_when_no_receipt(tx_id, asks, tmp_path):
    # With memos not skipped, so every row is drafted and its questions can be seen.
    assert chase(run("receipts/export.csv", context_dir=policy(tmp_path, skip_when_memo="false")),
                 tx_id)["ask_for"] == asks


def test_charges_that_already_have_a_memo_are_skipped():
    result = run("receipts/export.csv")
    for tx_id in ("rc_receipt_and_memo", "rc_memo_only"):
        assert chase(result, tx_id) == {"source": "rule", "status": "skip",
                                        "reason": "already has a memo", "ask_for": []}
    assert chase(result, "rc_none")["status"] == "draft"


def policy(tmp_path, **changes):
    """An override folder holding only a changed chase policy."""
    ctx = tmp_path / "context"
    ctx.mkdir(exist_ok=True)
    text = (ROOT / "context" / "chase-policy.yaml").read_text()
    for key, value in changes.items():
        line = next(l for l in text.splitlines() if l.startswith(f"{key}:"))
        text = text.replace(line, f"{key}: {value}")
    (ctx / "chase-policy.yaml").write_text(text)
    return ctx


def test_policy_can_skip_charges_with_receipt_and_memo(tmp_path):
    ctx = policy(tmp_path, skip_when_memo="false", skip_when_receipt_and_memo="true")
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
        ("mt_px_other_card", "mt_tx_other_card", "match"),
    }


def test_same_merchant_on_another_card_is_not_matched():
    # Visit 1 on card 7742 and the visit on card 1290 are the same merchant, same
    # day, same pending amount. Each must match the pending charge on its own card.
    result = run(EARLY, LATE)
    tx = next(t for t in result["transactions"] if t["id"] == "mt_tx_other_card")
    assert tx["inferred"]["pending_match"]["pending_transaction_id"] == "mt_px_other_card"


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


# --- an override folder replaces context files one by one --------------------

def test_override_folder_replaces_only_the_files_it_has(tmp_path):
    (tmp_path / "message-template.md").write_text("Ask about {merchant} on {card_last4}\n")
    (tmp_path / "cards.yaml").write_text(
        'status: real\ncards:\n  - {last4: "1290", cardholder: A, channel: "#travel-card"}\n')
    result = run("routing/export.csv", context_dir=tmp_path)
    assert draft(result, "rt_known") == {
        "id": "draft-rt_known", "transaction_id": "rt_known", "channel": "#travel-card",
        "needs_routing": False, "text": "Ask about Delta Air Lines on 1290\n"}
    versions = result["run"]["context"]
    assert versions["cards"]["from"] == "override" and versions["chase-policy"]["from"] == "default"


def test_template_flag_beats_the_override_folder(tmp_path):
    (tmp_path / "message-template.md").write_text("from the folder\n")
    flag = tmp_path / "flag.md"
    flag.write_text("from the flag\n")
    result = run("routing/export.csv", context_dir=tmp_path, template_path=flag)
    assert draft(result, "rt_known")["text"] == "from the flag\n"


# --- declined ----------------------------------------------------------------

def test_declined_charge_is_skipped_not_chased():
    result = run("declined/export.csv")
    assert chase(result, "dc_declined") == {"source": "rule", "status": "skip",
                                            "reason": "declined charge", "ask_for": []}
    assert chase(result, "dc_ok")["status"] == "draft"


# --- dropped columns never reach an output ----------------------------------

DROPPED = ["fake-spender.example", "receipts.fake-brex.example", "dashboard.fake-brex.example",
           "Fake Approver", "Fake Attendee", "Fake Team Budget", "Fake Card Policy",
           "Liabilities:2100", "15:30:00"]


def test_dropped_columns_never_reach_an_output(tmp_path):
    from chase_list import report
    result = run("baseline/brex-transactions-2026-09.csv", "three-day-exports/brex-export-2026-09-30.csv")
    written = "".join(p.read_text() for p in report.write(result, tmp_path)) + report.summary(result)
    leaked = [v for v in DROPPED if v in written]
    assert not leaked, f"dropped columns leaked into the output: {leaked}"


def test_a_sent_draft_logs_no_dropped_columns(tmp_path):
    result = run("baseline/brex-transactions-2026-09.csv")
    saved = tmp_path / "r.chase.json"
    saved.write_text(json.dumps(result, default=shape.to_json))
    cli.main(["sent", str(saved), "--log", str(tmp_path / "log.json")])
    logged = (tmp_path / "log.json").read_text()
    assert not [v for v in DROPPED if v in logged]


# --- the copies match sample-data/ -------------------------------------------

@pytest.mark.skipif(not SAMPLE_DATA.exists(), reason="sample-data/ not alongside this Cog")
@pytest.mark.parametrize("path", sorted(p.relative_to(FIXTURES) for p in FIXTURES.rglob("*")
                                        if p.suffix in (".csv", ".yaml")), ids=str)
def test_fixture_matches_sample_data(path):
    assert filecmp.cmp(FIXTURES / path, SAMPLE_DATA / path, shallow=False), \
        f"{path} differs from sample-data/{path}; change sample-data, then copy it here"


# --- a wrong --context fails instead of quietly using the defaults -----------

@pytest.mark.parametrize("make, message", [
    (lambda d: (d / "vendors.yaml").write_text("vendors: []\n") and d / "vendors.yaml", "takes a folder, not a file"),
    (lambda d: d / "nope", "folder not found"),
    (lambda d: (d / "notes.txt").write_text("x") and d, "has none of"),
])
def test_wrong_context_is_an_error(make, message, tmp_path):
    from chase_list import context
    with pytest.raises(context.ContextError, match=message):
        context.load(make(tmp_path))


# --- after-auto-coder: the auto-coder's updated statement as input --------------

AFTER = "after-auto-coder/brex-transactions-2026-09.upload.csv"


@pytest.fixture(scope="module")
def after():
    return run(AFTER)


def test_only_charges_without_a_memo_are_drafted(after):
    for tx in after["transactions"]:
        if tx["inferred"]["chase"]["status"] == "draft":
            assert not tx["parsed"]["memo"], tx["id"]
    drafted = sorted(t["parsed"]["merchant_name"] for t in after["transactions"]
                     if t["inferred"]["chase"]["status"] == "draft")
    assert len(drafted) == 15 and "Delta Air Lines" in drafted and "Marriott" in drafted


def test_no_subscription_is_drafted(after):
    for tx in after["transactions"]:
        if "Paid by OT, Serving" in (tx["parsed"]["memo"] or ""):
            assert chase(after, tx["id"])["reason"] == "already has a memo", tx["id"]


def test_pending_subscription_waits_for_its_memo(after):
    # The pending AWS charge: no memo yet, but AWS's posted rows carry the subscription memo.
    assert chase(after, "px_0928a") == {
        "source": "rule", "status": "skip", "ask_for": [],
        "reason": "pending charge from a subscription vendor; it gets its memo once posted"}


def test_pending_one_offs_are_still_chased_early(after):
    assert chase(after, "px_0929b")["status"] == "draft"      # Marriott hold


def test_raw_export_warns_that_subscriptions_will_be_chased():
    raw = run("baseline/brex-transactions-2026-09.csv")
    assert any("is this the raw Brex export" in w for w in raw["run"]["warnings"])
    assert not any("is this the raw Brex export" in w for w in run(AFTER)["run"]["warnings"])


# --- the cardholder's name in the draft ----------------------------------------

def test_draft_names_the_cardholder():
    text = draft(run("routing/export.csv"), "rt_known")["text"]
    assert text.startswith("A charge on the card ending 1290 (Alex Rivera) needs a few details")


def test_draft_says_so_when_the_name_is_missing():
    # rt_no_card has neither a card number nor a name on the export.
    text = draft(run("routing/export.csv"), "rt_no_card")["text"]
    assert "card ending ???? (name not on the export)" in text
