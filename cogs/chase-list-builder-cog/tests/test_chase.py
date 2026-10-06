"""Checks on the synthetic fixtures: what gets chased, where it goes, what the
message says, and that nothing is chased twice."""
import csv
import filecmp
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from chase_list import cli, context, core, log
from cog_transactions import shape

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evaluation" / "fixtures"
MONTH = FIXTURES / "brex-transactions-2026-09.csv"
EXPORT_27 = FIXTURES / "brex-export-2026-09-27.csv"
EXPORT_30 = FIXTURES / "brex-export-2026-09-30.csv"


def validator():
    schemas = {name: json.loads((ROOT / "context" / name).read_text())
               for name in ("transaction.schema.json", "output-schema.json")}
    registry = Registry().with_resources(
        (name, Resource.from_contents(schema)) for name, schema in schemas.items())
    return Draft202012Validator(schemas["output-schema.json"], registry=registry,
                                format_checker=Draft202012Validator.FORMAT_CHECKER)


def as_json(result):
    return json.loads(json.dumps(result, default=shape.to_json))


def by_id(result, tx_id):
    return next(tx for tx in result["transactions"] if tx["id"] == tx_id)


def chase(result, tx_id):
    return by_id(result, tx_id)["inferred"]["chase"]


def draft_text(result, tx_id):
    return next(d["text"] for d in result["drafts"] if d["transaction_id"] == tx_id)


def rewrite(src, dst, change):
    """Copy a fixture, applying change(row) to every row."""
    with src.open() as f, dst.open("w", newline="") as g:
        reader = csv.DictReader(f)
        writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            change(row)
            writer.writerow(row)
    return dst


@pytest.fixture(scope="module")
def month():
    return core.run([MONTH])


# --- the contract ---

def test_output_matches_the_schema(month):
    validator().validate(as_json(month))


def test_output_example_matches_the_schema():
    validator().validate(json.loads((ROOT / "context" / "output-example.json").read_text()))


def test_every_row_appears_once_and_gets_a_decision(month):
    with MONTH.open() as f:
        ids = sorted(r["transaction_id"] for r in csv.DictReader(f))
    assert sorted(tx["id"] for tx in month["transactions"]) == ids
    assert all("chase" in tx["inferred"] for tx in month["transactions"])


def test_one_draft_per_chased_charge(month):
    chased = [tx["id"] for tx in month["transactions"]
              if tx["inferred"]["chase"]["status"] in ("draft", "needs-routing")]
    assert sorted(d["transaction_id"] for d in month["drafts"]) == sorted(chased)


def test_run_is_strict_with_no_binding(month):
    assert month["run"]["mode"] == "strict" and month["run"]["binding"] is None


# --- what gets chased ---

def test_refund_is_skipped(month):
    assert chase(month, "tx_0922a") == {"source": "rule", "status": "skip", "reason": "refund", "ask_for": []}


def test_pending_charge_is_chased_and_says_so(month):
    assert chase(month, "px_0929b")["status"] == "draft"          # Marriott $1.00 card check
    assert "pending: the amount may change" in draft_text(month, "px_0929b")


def test_receipt_question_dropped_when_receipt_attached(month):
    assert chase(month, "tx_0901a")["ask_for"] == ["purpose", "department"]        # GitHub, receipt on file
    assert chase(month, "tx_0910c")["ask_for"] == ["purpose", "department", "receipt"]


def test_auto_coder_output_skips_what_it_coded(tmp_path):
    coded = tmp_path / "coded.json"
    coded.write_text(json.dumps({
        "run": {"cog": "recurring-subscription-auto-coder-cog"},
        "transactions": [
            {"id": "tx_0901a", "inferred": {"coding": {"status": "proposed"}}},
            {"id": "tx_0918a", "inferred": {"coding": {"status": "needs-human"}}},
        ],
    }))
    result = core.run([MONTH], coded_path=coded)
    assert chase(result, "tx_0901a")["status"] == "skip"
    assert chase(result, "tx_0918a")["reason"] == "the auto-coder couldn't code it"


def test_other_json_is_refused_as_auto_coder_output(tmp_path):
    bogus = tmp_path / "x.json"
    bogus.write_text('{"run": {"cog": "something-else"}, "transactions": []}')
    with pytest.raises(ValueError, match="isn't output from"):
        core.run([MONTH], coded_path=bogus)


# --- where it goes ---

def test_routed_to_the_cards_channel(month):
    assert by_id(month, "tx_0910c")["inferred"]["route"]["channel"] == "#card-1290"


def test_unknown_card_needs_routing(tmp_path):
    def change(row):
        if row["transaction_id"] == "tx_0910c":
            row["card_last4"] = "9999"
    result = core.run([rewrite(MONTH, tmp_path / "m.csv", change)])
    assert chase(result, "tx_0910c")["status"] == "needs-routing"
    d = next(d for d in result["drafts"] if d["transaction_id"] == "tx_0910c")
    assert d["channel"] is None and d["needs_routing"]


# --- the template ---

def test_custom_template_is_used(tmp_path):
    t = tmp_path / "t.md"
    t.write_text("{vendor} {amount} {{literal}}\n{reply_form}\n")
    result = core.run([MONTH], template_path=t)
    assert draft_text(result, "tx_0910c") == "delta 684.40 {literal}\nref: tx_0910c\npurpose:\ndepartment:\nreceipt:\n"


def test_unknown_placeholder_fails_at_load(tmp_path):
    t = tmp_path / "t.md"
    t.write_text("Amount: {amonut}\n")
    with pytest.raises(context.ContextError, match="amonut"):
        core.run([MONTH], template_path=t)


def test_export_text_cant_ping_a_channel(tmp_path):
    def change(row):
        if row["transaction_id"] == "tx_0910c":
            row["merchant_descriptor"] = "@channel <!here> SHOP"
    result = core.run([rewrite(MONTH, tmp_path / "m.csv", change)])
    text = draft_text(result, "tx_0910c")
    assert "@" not in text and "<!" not in text


# --- data is never direction ---

def test_memo_never_reaches_a_draft(month):
    memos = [tx["parsed"]["memo"] for tx in month["transactions"] if tx["parsed"]["memo"]]
    assert memos
    for d in month["drafts"]:
        assert not any(m in d["text"] for m in memos)


def test_injection_fixture_changes_nothing(tmp_path):
    result = core.run([FIXTURES / "injection.csv"])
    validator().validate(as_json(result))

    def blank(row):
        row["memo"] = ""
        row["cardholder"] = "Someone"
    clean = core.run([rewrite(FIXTURES / "injection.csv", tmp_path / "c.csv", blank)])
    decisions = lambda r: {tx["id"]: tx["inferred"]["chase"] for tx in r["transactions"]}
    assert decisions(result) == decisions(clean)
    assert all("Ignore" not in d["text"] and "Note to the AI" not in d["text"] for d in result["drafts"])


# --- exports of any length ---

def test_overlapping_exports_are_deduplicated():
    result = core.run([MONTH, EXPORT_30])
    assert sorted(tx["id"] for tx in result["transactions"]) == sorted(tx["id"] for tx in core.run([MONTH])["transactions"])
    assert result["run"]["counts"]["duplicates_dropped"] == 7


def test_pending_replaced_by_posted_across_exports():
    result = core.run([EXPORT_27, EXPORT_30])
    ids = {tx["id"] for tx in result["transactions"]}
    assert "px_0925a" not in ids and "px_0926z" not in ids
    assert {(s["pending_id"], s["how"]) for s in result["superseded"]} == {("px_0925a", "export"), ("px_0926z", "match")}
    assert by_id(result, "tx_0926a")["inferred"]["pending_match"]["source"] == "match"
    assert any("tx_0926a" in w for w in result["run"]["warnings"])


def test_a_later_visit_isnt_matched_to_an_earlier_pending_charge():
    # Lucky Bar pending on the 30th is a different visit from the one posted on the 26th.
    result = core.run([EXPORT_27, EXPORT_30])
    assert chase(result, "px_0930b")["status"] == "draft"


# --- never chased twice ---

def test_chase_log_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("INIT_CWD", str(tmp_path))
    log_path = tmp_path / "chase-log.json"

    first = core.run([EXPORT_27], log_path=log_path)
    assert first["run"]["counts"]["drafts"] == 3
    assert not log_path.exists()                     # drafting records nothing

    out = tmp_path / "first.chase.json"
    out.write_text(json.dumps(first, default=shape.to_json))
    cli.main(["sent", str(out), "--log", str(log_path)])
    assert len(log.read(log_path)) == 3

    second = core.run([EXPORT_30], log_path=log_path)
    assert chase(second, "tx_0925a")["status"] == "already-chased"     # linked in the export
    assert chase(second, "tx_0926a")["status"] == "already-chased"     # matched
    assert by_id(second, "tx_0926a")["inferred"]["pending_match"]["pending_transaction_id"] == "px_0926z"
    assert chase(second, "px_0930b")["status"] == "draft"              # a new visit
    validator().validate(as_json(second))


def test_sent_can_record_just_some_drafts(tmp_path):
    result = core.run([EXPORT_27])
    out = tmp_path / "r.chase.json"
    out.write_text(json.dumps(result, default=shape.to_json))
    cli.main(["sent", str(out), "--only", "draft-px_0925a", "--log", str(tmp_path / "log.json")])
    assert [e["transaction_id"] for e in log.read(tmp_path / "log.json")] == ["px_0925a"]


# --- the shared files are copies, and must stay identical ---

AUTO_CODER = ROOT.parent / "recurring-subscription-auto-coder-cog"


@pytest.mark.skipif(not AUTO_CODER.exists(), reason="auto-coder not alongside this Cog")
@pytest.mark.parametrize("path", [
    "src/cog_transactions/__init__.py", "src/cog_transactions/shape.py",
    "src/cog_transactions/load.py", "src/cog_transactions/vendors.py",
    "src/cog_transactions/combine.py",
    "context/transaction.schema.json", "context/vendors.yaml",
])
def test_shared_file_matches_the_auto_coders_copy(path):
    assert filecmp.cmp(ROOT / path, AUTO_CODER / path, shallow=False), \
        f"{path} differs from the auto-coder's copy; change one, then copy it to the other"
